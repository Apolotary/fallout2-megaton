#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Sustainable-Use
"""Fallout 2 script toolchain: compile .ssl, inspect .int, pack a patch archive.

    ssl.py compile <file.ssl> -o <out.int> [-I dir]... [-D NAME[=VALUE]]... [-O 0..2] [-s] [-w] [-v]
    ssl.py disasm  <file.int> [--summary]
    ssl.py pack    <staging dir> -o <patch001.dat> [--store]
    ssl.py setup                         (re)build the compiler from tools/sslc

compile runs sfall's sslc (tools/sslc, built to WebAssembly, executed by node)
with its built-in C preprocessor, so #include/#define/#ifdef and // comments
work and errors carry the real file and line. mod/scripts_src/headers is always
on the include path. The result is re-read with tools/intfile.py and linted for
things fallout2-ce handles badly. Exit status is non-zero on any error and the
output file is only replaced by a successful compile.

pack writes a DAT2 archive from a directory that mirrors the game's virtual
paths (scripts/, text/english/dialog/, maps/, data/, ...). Files that already
exist in patch000.dat (scripts.lst, scrname.msg, vault13.gam, ...) can only be
overridden from an archive named patch001.dat or higher, not from loose files.
"""
import argparse
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

if __name__ == "ssl":
    # Every script started from tools/ has this folder first on sys.path, so the
    # standard library's own `import ssl` (urllib, http.client, asyncio, ...) would
    # get this file. Hand such importers the real module instead. To use the
    # functions below from Python, load this file under another name
    # (importlib.util.spec_from_file_location("fo2ssl", ".../tools/ssl.py")).
    import importlib.util
    import sysconfig

    _spec = importlib.util.spec_from_file_location("ssl", os.path.join(sysconfig.get_path("stdlib"), "ssl.py"))
    _stdlib_ssl = importlib.util.module_from_spec(_spec)
    sys.modules["ssl"] = _stdlib_ssl
    _spec.loader.exec_module(_stdlib_ssl)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intfile  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSLC_DIR = os.path.join(ROOT, "tools", "sslc")
SSLC_MODULE = os.path.join(SSLC_DIR, "build", "bin", "sslc.mjs")
DEFAULT_INCLUDE = os.path.join(ROOT, "mod", "scripts_src", "headers")

# Runs the Emscripten module (NODERAWFS: it sees the real file system) in the
# current directory. Upstream's compiler.mjs does the same but strips anything
# after the last dot of the working directory name, which breaks e.g. "v1.2/".
NODE_LAUNCHER = """
import { pathToFileURL } from "node:url";
const [modulePath, ...args] = process.argv.slice(1);
const { default: Module } = await import(pathToFileURL(modulePath).href);
const lines = [];
let status = 1;
try {
    const instance = await Module({ print: (t) => lines.push(t), printErr: (t) => lines.push(t), noInitialRun: true });
    instance.FS.chdir(process.cwd());
    status = instance.callMain(args);
} catch (error) {
    lines.push("sslc crashed: " + (error && error.stack ? error.stack : error));
}
process.stdout.write(lines.join("\\n") + "\\n", () => process.exit(status));
"""

WRAPPER_NAME = "wrapper.ssl"

# sslc chatter that is not a diagnostic.
NOISE_PREFIXES = ("Compiling ", "Set include directory", "Add include directory", "Define macro")


class ToolError(Exception):
    pass


def run_sslc(args, cwd):
    """Runs sslc with `args` in `cwd`; returns (exit status, output lines)."""
    if not os.path.exists(SSLC_MODULE):
        raise ToolError("compiler not built: %s is missing (run: python3 tools/ssl.py setup)" % SSLC_MODULE)
    node = shutil.which("node")
    if node is None:
        raise ToolError("node not found on PATH")
    proc = subprocess.run([node, "--input-type=module", "-e", NODE_LAUNCHER, "--", SSLC_MODULE] + args,
                          cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    return proc.returncode, [line for line in proc.stdout.splitlines() if line.strip()]


def merge_include_dirs(dirs, merged):
    """sslc searches only the first and the last -I directory. For longer lists, build one
    directory of symlinks to the entries of all of them (earlier directories win)."""
    os.mkdir(merged)
    for directory in dirs:
        for name in sorted(os.listdir(directory)):
            link = os.path.join(merged, name)
            if not os.path.lexists(link):
                os.symlink(os.path.join(directory, name), link)
    return merged


def compile_ssl(source, output, include_dirs=(), defines=(), optimize=2, short_circuit=False, warnings=False):
    """Compiles `source` to `output`. Returns (IntFile, diagnostics); raises ToolError on failure.

    sslc only opens bare file names in its working directory and honours a single
    -m macro, so the real input is a generated wrapper in a scratch directory:
    the #defines followed by an #include of the source by absolute path. Includes
    inside the source still resolve relative to the source's own directory.
    """
    source = os.path.abspath(source)
    output = os.path.abspath(output)
    if not os.path.isfile(source):
        raise ToolError("no such file: %s" % source)
    os.makedirs(os.path.dirname(output), exist_ok=True)

    args = ["-q", "-l", "-p", "-F", "-O%d" % optimize]
    if not warnings:
        args.append("-n")
    if short_circuit:
        args.append("-s")
    dirs = [os.path.abspath(d) for d in include_dirs]
    if os.path.isdir(DEFAULT_INCLUDE) and DEFAULT_INCLUDE not in dirs:
        dirs.append(DEFAULT_INCLUDE)
    for directory in dirs:
        if not os.path.isdir(directory):
            raise ToolError("include directory not found: %s" % directory)

    wrapper = []
    for define in defines:
        name, _, value = define.partition("=")
        if not name.replace("_", "a").isalnum() or name[0].isdigit():
            raise ToolError("bad macro name: %r" % define)
        wrapper.append("#define %s %s\n" % (name, value or "1"))
    wrapper.append('#include "%s"\n' % source.replace("\\", "/"))

    with tempfile.TemporaryDirectory(prefix="sslc") as work:
        with open(os.path.join(work, WRAPPER_NAME), "w") as f:
            f.writelines(wrapper)
        merged = None
        if len(dirs) > 2:
            merged = merge_include_dirs(dirs, os.path.join(work, "include"))
            dirs = [merged]
        result = os.path.join(work, "out.int")
        status, lines = run_sslc(args + ["-I" + d for d in dirs] + [WRAPPER_NAME, "-o", result], work)
        # Warnings sslc raises after parsing (e.g. "Procedure x not referenced") name its
        # top-level input, the wrapper, next to the line number in the real source.
        diagnostics = [line.replace("<%s>" % WRAPPER_NAME, "<%s>" % source)
                       for line in lines if not line.startswith(NOISE_PREFIXES)]
        if merged:
            real = lambda m: os.path.realpath(m.group(0))
            diagnostics = [re.sub(re.escape(merged) + r"/[^/<>:\"]+", real, line) for line in diagnostics]
        if status != 0 or not os.path.exists(result):
            # sslc exits 0 with only a warning when it cannot find the input file.
            raise ToolError("\n".join(diagnostics) or "sslc failed with status %d and no output" % status)
        with open(result, "rb") as f:
            data = f.read()
    try:
        script = intfile.IntFile(data, output)
    except intfile.IntError as error:
        raise ToolError("sslc produced an unreadable file: %s" % error)
    with open(output, "wb") as f:
        f.write(data)
    return script, diagnostics


def write_dat2(path, files, compress=True):
    """Writes a Fallout 2 DAT2 archive. files: {"dir/name.ext": bytes}.

    Layout (little-endian): payloads, entry table (count, then per entry: name
    length, name with backslashes, compressed flag, real size, packed size,
    offset), table size, archive size. The engine binary-searches the table
    case-insensitively (src/dfile.cc), hence the sort key.
    """
    names = sorted(files, key=lambda n: n.replace("/", "\\").lower())
    tree = bytearray(struct.pack("<I", len(names)))
    with open(path, "wb") as f:
        offset = 0
        for name in names:
            data = files[name]
            encoded = name.replace("/", "\\").encode("latin-1")
            packed = zlib.compress(data, 9) if compress and data else data
            f.write(packed)
            tree += struct.pack("<I", len(encoded)) + encoded
            tree += struct.pack("<BIII", 1 if packed is not data else 0, len(data), len(packed), offset)
            offset += len(packed)
        f.write(tree)
        f.write(struct.pack("<II", len(tree), offset + len(tree) + 8))


def pack_directory(staging, output, compress=True):
    """Packs every file under `staging` into a DAT2 archive; returns the sorted entry names."""
    files = {}
    seen = {}
    for base, dirs, names in os.walk(staging):
        dirs.sort()
        for name in sorted(names):
            if name.startswith("."):
                continue
            full = os.path.join(base, name)
            rel = os.path.relpath(full, staging).replace(os.sep, "/")
            if rel.lower() in seen:
                raise ToolError("two files differ only by case: %s and %s" % (seen[rel.lower()], rel))
            seen[rel.lower()] = rel
            with open(full, "rb") as f:
                files[rel] = f.read()
    if not files:
        raise ToolError("nothing to pack in %s" % staging)
    write_dat2(output, files, compress)
    return sorted(files, key=str.lower)


def summary(script):
    names = script.procedure_names()
    lines = ["%s: %d bytes, %d procedures, %d strings" % (script.name, len(script.data), len(names), len(script.strings)),
             "  handlers: %s" % (", ".join(script.handlers()) or "none"),
             "  procedure #1 (fallback for unhandled events): %s" % (names[0] if names else "none"),
             "  local_vars needed: >= %d" % script.local_vars_needed()]
    return lines + ["  warning: %s" % w for w in script.lint()]


def cmd_compile(args):
    output = args.output or os.path.splitext(args.source)[0] + ".int"
    script, diagnostics = compile_ssl(args.source, output, args.include, args.define, args.optimize,
                                      args.short_circuit, args.warnings)
    for line in diagnostics:
        print(line, file=sys.stderr)
    for warning in script.lint():
        print("%s: warning: %s" % (args.source, warning), file=sys.stderr)
    if args.verbose:
        print("\n".join(summary(script)))
    return 0


def cmd_disasm(args):
    status = 0
    for path in args.files:
        try:
            script = intfile.load(path)
        except (OSError, intfile.IntError) as error:
            print("%s: %s" % (path, error), file=sys.stderr)
            status = 1
            continue
        sys.stdout.write("\n".join(summary(script)) + "\n" if args.summary else script.disassemble())
    return status


def cmd_pack(args):
    names = pack_directory(args.staging, args.output, not args.store)
    print("%s: %d files, %d bytes" % (args.output, len(names), os.path.getsize(args.output)))
    if args.verbose:
        for name in names:
            print("  " + name)
    return 0


def cmd_setup(args):
    """Builds tools/sslc to WebAssembly with the local Emscripten (the upstream CI recipe)."""
    build = os.path.join(SSLC_DIR, "build")
    for tool in ("emcmake", "emmake", "cmake"):
        if shutil.which(tool) is None:
            raise ToolError("%s not found on PATH" % tool)
    if not os.path.exists(os.path.join(SSLC_DIR, "CMakeLists.txt")):
        raise ToolError("%s is missing: git clone https://github.com/sfall-team/sslc tools/sslc" % SSLC_DIR)
    os.makedirs(build, exist_ok=True)
    subprocess.run(["emcmake", "cmake", "-DCMAKE_BUILD_TYPE=Release", ".."], cwd=build, check=True)
    subprocess.run(["emmake", "make"], cwd=build, check=True)
    status, lines = run_sslc([], build)
    print(lines[0] if lines else "sslc printed nothing (status %d)" % status)
    return 0 if lines and "compiler" in lines[0] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("compile", help="preprocess and compile one .ssl file")
    p.add_argument("source")
    p.add_argument("-o", "--output", help="output .int (default: next to the source)")
    p.add_argument("-I", "--include", action="append", default=[], metavar="DIR", help="extra include directory")
    p.add_argument("-D", "--define", action="append", default=[], metavar="NAME[=VALUE]", help="predefine a macro")
    p.add_argument("-O", "--optimize", type=int, choices=(0, 1, 2), default=2,
                   help="0 none, 1 drop unreferenced procedures/variables, 2 full (default)")
    p.add_argument("-s", "--short-circuit", action="store_true", help="short-circuit `and`/`or` (like #pragma sce)")
    p.add_argument("-w", "--warnings", action="store_true", help="show sslc warnings")
    p.add_argument("-v", "--verbose", action="store_true", help="print a summary of the compiled script")
    p.set_defaults(func=cmd_compile)

    p = sub.add_parser("disasm", help="disassemble .int files")
    p.add_argument("files", nargs="+")
    p.add_argument("--summary", action="store_true", help="only procedures/handlers/warnings")
    p.set_defaults(func=cmd_disasm)

    p = sub.add_parser("pack", help="pack a staging directory into a DAT2 archive")
    p.add_argument("staging")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--store", action="store_true", help="do not compress")
    p.add_argument("-v", "--verbose", action="store_true", help="list the packed files")
    p.set_defaults(func=cmd_pack)

    p = sub.add_parser("setup", help="build the sslc compiler (needs emcmake, cmake, node)")
    p.set_defaults(func=cmd_setup)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ToolError as error:
        print(str(error), file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print("command failed: %s" % " ".join(error.cmd), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
