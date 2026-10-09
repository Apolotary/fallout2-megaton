"""FRM art (and the per-direction ``.fr0`` .. ``.fr5`` variants).

Big-endian. 62-byte header, then for every *stored* direction `frame_count`
frames of ``u16 width, u16 height, u32 size, i16 x, i16 y, pixels[size]``
(art.cc:1034-1144). Pixels are palette indices, index 0 is transparent.

Directions are 0..5 = NE, E, SE, SW, W, NW. A file stores one direction
(tiles, walls, scenery, most items: every rotation shows the same frames) or
six (critters). The header's per-direction `x_offsets` / `y_offsets` shift
the whole sprite and may differ per rotation even with one stored direction.

Placement of a still object (object.cc:4881-4923): the frame's bottom-centre
pixel sits on the hex centre moved by the direction's header shift and the
object's own x / y - see `Frm.placement`. Per-frame x / y only matter to the
animation code.

    art = GameFiles().art                       # ArtDB
    frm = art.load(0x02000001)                  # by FID
    img = frm.image(gf.palette, direction=0)    # PIL RGBA
    new = Frm.from_rgba([rgba], gf.palette, shift=(0, 0)).to_bytes()
"""
import struct

import numpy as np

from . import ids

HEADER_SIZE = 62


class Frame:
    """One frame: `pixels` is `width * height` palette indices, row-major."""

    __slots__ = ("width", "height", "x", "y", "pixels")

    def __init__(self, width, height, pixels, x=0, y=0):
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.pixels = bytes(pixels)

    def array(self):
        """(height, width) uint8 view of the palette indices."""
        return np.frombuffer(self.pixels, dtype=np.uint8).reshape(self.height, self.width)


class Frm:
    def __init__(self):
        self.version = 4
        self.fps = 0
        self.action_frame = 0
        self.x_offsets = [0] * 6
        self.y_offsets = [0] * 6
        self.stored = []                  # stored directions, each a list of Frame
        self.direction_map = [0] * 6      # direction -> index into `stored`
        self.data_size_override = None    # .frN files carry the size of the whole set

    # ---------------------------------------------------------------- queries
    @property
    def frame_count(self):
        return len(self.stored[0]) if self.stored else 0

    @property
    def direction_count(self):
        """Number of directions stored in the file (1 or 6 in retail data)."""
        return len(self.stored)

    def frames(self, direction=0):
        return self.stored[self.direction_map[direction]]

    def frame(self, direction=0, index=0):
        return self.frames(direction)[index]

    def size(self, direction=0, index=0):
        frame = self.frame(direction, index)
        return frame.width, frame.height

    def shift(self, direction=0):
        """Header (x, y) shift of a direction."""
        return self.x_offsets[direction], self.y_offsets[direction]

    def placement(self, direction=0, index=0, obj_x=0, obj_y=0):
        """(left, top, width, height) of the frame relative to the hex centre."""
        frame = self.frame(direction, index)
        anchor_x = self.x_offsets[direction] + obj_x
        anchor_y = self.y_offsets[direction] + obj_y
        return anchor_x - frame.width // 2, anchor_y - (frame.height - 1), frame.width, frame.height

    def rgba(self, palette, direction=0, index=0):
        """(height, width, 4) uint8 RGBA."""
        return palette.rgba[self.frame(direction, index).array()]

    def image(self, palette, direction=0, index=0):
        from PIL import Image
        return Image.fromarray(self.rgba(palette, direction, index), "RGBA")

    # -------------------------------------------------------------- serialise
    @classmethod
    def from_bytes(cls, data):
        self = cls()
        self.version, self.fps, self.action_frame, frame_count = struct.unpack_from(">IHHH", data, 0)
        self.x_offsets = list(struct.unpack_from(">6h", data, 10))
        self.y_offsets = list(struct.unpack_from(">6h", data, 22))
        data_offsets = struct.unpack_from(">6I", data, 34)
        (data_size,) = struct.unpack_from(">I", data, 58)
        pos = HEADER_SIZE
        for direction in range(6):
            # art.cc:1129-1139: a direction is read (sequentially) only when its
            # offset differs from the previous direction's.
            if direction > 0 and data_offsets[direction] == data_offsets[direction - 1]:
                self.direction_map[direction] = len(self.stored) - 1
                continue
            frames = []
            for _ in range(frame_count):
                width, height, size, x, y = struct.unpack_from(">HHIhh", data, pos)
                pixels = data[pos + 12:pos + 12 + size]
                if len(pixels) != size or size != width * height:
                    raise ValueError("truncated or inconsistent FRM frame")
                frames.append(Frame(width, height, pixels, x, y))
                pos += 12 + size
            self.direction_map[direction] = len(self.stored)
            self.stored.append(frames)
        if data_size != pos - HEADER_SIZE:
            self.data_size_override = data_size
        return self

    def to_bytes(self):
        body = bytearray()
        starts = []
        for frames in self.stored:
            if len(frames) != self.frame_count:
                raise ValueError("every direction needs the same number of frames")
            starts.append(len(body))
            for frame in frames:
                if len(frame.pixels) != frame.width * frame.height:
                    raise ValueError("frame pixel count does not match its size")
                body += struct.pack(">HHIhh", frame.width, frame.height, len(frame.pixels), frame.x, frame.y)
                body += frame.pixels
        data_size = len(body) if self.data_size_override is None else self.data_size_override
        head = struct.pack(">IHHH", self.version, self.fps, self.action_frame, self.frame_count)
        head += struct.pack(">6h", *self.x_offsets) + struct.pack(">6h", *self.y_offsets)
        head += struct.pack(">6I", *(starts[self.direction_map[d]] for d in range(6)))
        head += struct.pack(">I", data_size)
        return head + bytes(body)

    # ----------------------------------------------------------------- encode
    @staticmethod
    def frame_from_rgba(rgba, palette, x=0, y=0, alpha_threshold=128, exact=True):
        """(h, w, 4) RGBA -> Frame; pixels with alpha below the threshold become transparent."""
        rgba = np.asarray(rgba, dtype=np.uint8)
        if rgba.ndim != 3 or rgba.shape[2] != 4:
            raise ValueError("expected an (h, w, 4) RGBA array")
        indices = palette.quantise(rgba[:, :, :3], exact=exact)
        indices = np.where(rgba[:, :, 3] >= alpha_threshold, indices, 0).astype(np.uint8)
        return Frame(rgba.shape[1], rgba.shape[0], indices.tobytes(), x, y)

    @classmethod
    def from_rgba(cls, images, palette, shift=(0, 0), fps=0, action_frame=0, alpha_threshold=128, exact=True):
        """Build an FRM from RGBA images (numpy arrays or PIL images).

        images  a list of frames (one stored direction), or a list of six such
                lists (one per direction NE..NW).
        shift   header shift: one (x, y) for all directions or six pairs.
        """
        if images and isinstance(images[0], (list, tuple)):
            directions = [list(d) for d in images]
            if len(directions) != 6:
                raise ValueError("give either one direction or all six")
        else:
            directions = [list(images)]
        self = cls()
        self.fps = fps
        self.action_frame = action_frame
        shifts = [shift] * 6 if isinstance(shift[0], int) else list(shift)
        self.x_offsets = [s[0] for s in shifts]
        self.y_offsets = [s[1] for s in shifts]
        self.stored = [[cls.frame_from_rgba(np.asarray(image.convert("RGBA")) if hasattr(image, "convert") else image,
                                            palette, alpha_threshold=alpha_threshold, exact=exact)
                        for image in frames] for frames in directions]
        self.direction_map = list(range(6)) if len(directions) == 6 else [0] * 6
        return self


def critter_suffix(anim, weapon):
    """Two-letter file suffix of a critter animation (_art_get_code, art.cc:544-612), or None."""
    if not 0 <= weapon <= 10:
        return None
    if 38 <= anim <= 47:                                  # take out .. fire continuous
        return None if weapon == 0 else chr(ord("d") + weapon - 1) + chr(ord("c") + anim - 38)
    if anim == 36:
        return "ch"
    if anim == 37:
        return "cj"
    if anim == 64:
        return "na"
    if anim >= 48:                                        # single-frame deaths
        return "r" + chr(ord("a") + anim - 48)
    if anim >= 20:                                        # knockdown / death
        return "b" + chr(ord("a") + anim - 20)
    if anim == 18:                                        # throw
        return {1: "dm", 4: "gm"}.get(weapon, "as")
    if anim == 13:                                        # dodge
        return "an" if weapon <= 0 else chr(ord("d") + weapon - 1) + "e"
    first = chr(ord("d") + weapon - 1) if (anim <= 1 and weapon > 0) else "a"
    return first + chr(ord("a") + anim)


class ArtDB:
    """FID -> art file over a `GameFiles` tree (decoded files are cached)."""

    def __init__(self, gamefiles, cache_size=2048):
        self.gf = gamefiles
        self._cache = {}
        self._cache_size = cache_size

    def fid(self, obj_type, name):
        """FID of an art file name such as 'edg5000.frm' (first list entry with that name)."""
        return ids.make_fid(obj_type, self.gf.art_list(obj_type).index(name))

    def name(self, fid):
        """Art list entry of a FID (critters: the 6-letter base name), or None."""
        obj_type = ids.fid_type(fid)
        if obj_type >= len(ids.TYPE_DIRS):
            return None
        return self.gf.art_list(obj_type).name(ids.fid_index(fid))

    def path(self, fid):
        """Game-tree path the engine opens for a FID (artBuildFilePath), or None.

        Talking heads and the animation aliases of artAliasFid are not handled.
        """
        obj_type = ids.fid_type(fid)
        name = self.name(fid)
        if not name or obj_type == ids.OBJ_TYPE_HEAD:
            return None
        directory = f"art/{ids.TYPE_DIRS[obj_type]}/"
        if obj_type != ids.OBJ_TYPE_CRITTER:
            return directory + name.lower()
        suffix = critter_suffix(ids.fid_anim(fid), ids.fid_weapon(fid))
        if suffix is None:
            return None
        rotation = ids.fid_rotation(fid)
        extension = f".fr{rotation - 1}" if rotation else ".frm"
        return directory + name.lower() + suffix + extension

    def exists(self, fid):
        path = self.path(fid)
        return path is not None and self.gf.exists(path)

    def load(self, fid):
        """Decoded `Frm` for a FID; raises FileNotFoundError when there is no art."""
        frm = self._cache.get(fid)
        if frm is None:
            path = self.path(fid)
            if path is None:
                raise FileNotFoundError(f"no art path for FID 0x{fid:08X}")
            frm = Frm.from_bytes(self.gf.read(path))
            if len(self._cache) >= self._cache_size:
                self._cache.clear()
            self._cache[fid] = frm
        return frm
