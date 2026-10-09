# SPDX-License-Identifier: MIT
"""A very small vocabulary for building shader node trees from Python (Blender 5.x).

    g = Graph("my material")
    p = g.coords()                               # object-space position in metres
    n = g.noise(p, scale=3.0, detail=4)          # 0..1 value socket
    colour = g.ramp(n, [(0.3, (0.2, 0.1, 0.05)), (0.7, (0.5, 0.5, 0.5))])
    g.principled(base=colour, roughness=0.8, bump=g.bump(n, 0.02))
    material = g.material

Every helper takes sockets or plain numbers / tuples and returns an output
socket, so graphs read like expressions. Object space is used everywhere, in
metres, so a texture keeps its real-world scale on any mesh and does not
depend on UVs.
"""
import bpy


def _is_socket(value):
    return isinstance(value, bpy.types.NodeSocket)


def _rgba(value):
    if len(value) == 3:
        return (value[0], value[1], value[2], 1.0)
    return tuple(value)


class Graph:
    def __init__(self, name):
        self.material = bpy.data.materials.new(name)
        self.material.use_nodes = True
        self.tree = self.material.node_tree
        self.nodes = self.tree.nodes
        self.links = self.tree.links
        self.nodes.clear()
        self.output = self.nodes.new("ShaderNodeOutputMaterial")

    # ------------------------------------------------------------- plumbing
    def new(self, kind, **attributes):
        node = self.nodes.new(kind)
        for key, value in attributes.items():
            setattr(node, key, value)
        return node

    def put(self, socket, value):
        """Connect a socket or set its default."""
        if value is None:
            return
        if _is_socket(value):
            self.links.new(value, socket)
        elif hasattr(socket, "default_value"):
            current = socket.default_value
            if hasattr(current, "__len__") and not isinstance(value, (int, float)):
                value = _rgba(value) if len(current) == 4 else tuple(value)[:len(current)]
            elif hasattr(current, "__len__"):
                value = (value,) * len(current) if len(current) != 4 else (value, value, value, 1.0)
            socket.default_value = value

    @staticmethod
    def by_id(sockets, identifier):
        for socket in sockets:
            if socket.identifier == identifier:
                return socket
        raise KeyError(identifier)

    # ---------------------------------------------------------------- inputs
    def coords(self, kind="Object"):
        return self.new("ShaderNodeTexCoord").outputs[kind]

    def world_position(self):
        return self.new("ShaderNodeNewGeometry").outputs["Position"]

    def object_random(self):
        """0..1, different for every object: free variation between copies."""
        return self.new("ShaderNodeObjectInfo").outputs["Random"]

    def pointiness(self):
        return self.new("ShaderNodeNewGeometry").outputs["Pointiness"]

    def mapping(self, vector, scale=(1, 1, 1), location=(0, 0, 0), rotation=(0, 0, 0)):
        node = self.new("ShaderNodeMapping")
        self.put(node.inputs["Vector"], vector)
        self.put(node.inputs["Scale"], scale)
        self.put(node.inputs["Location"], location)
        self.put(node.inputs["Rotation"], rotation)
        return node.outputs[0]

    def separate(self, vector):
        node = self.new("ShaderNodeSeparateXYZ")
        self.put(node.inputs[0], vector)
        return node.outputs[0], node.outputs[1], node.outputs[2]

    def combine(self, x=0.0, y=0.0, z=0.0):
        node = self.new("ShaderNodeCombineXYZ")
        for socket, value in zip(node.inputs, (x, y, z)):
            self.put(socket, value)
        return node.outputs[0]

    # -------------------------------------------------------------- textures
    def noise(self, vector, scale=1.0, detail=3.0, roughness=0.55, distortion=0.0, colour=False):
        node = self.new("ShaderNodeTexNoise", noise_dimensions="3D")
        self.put(node.inputs["Vector"], vector)
        self.put(node.inputs["Scale"], scale)
        self.put(node.inputs["Detail"], detail)
        self.put(node.inputs["Roughness"], roughness)
        self.put(node.inputs["Distortion"], distortion)
        return node.outputs[1 if colour else 0]

    def voronoi(self, vector, scale=1.0, feature="F1", output="Distance", randomness=1.0):
        node = self.new("ShaderNodeTexVoronoi", feature=feature)
        self.put(node.inputs["Vector"], vector)
        self.put(node.inputs["Scale"], scale)
        self.put(node.inputs["Randomness"], randomness)
        return node.outputs[output]

    def white_noise(self, vector):
        node = self.new("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
        self.put(node.inputs["Vector"], vector)
        return node.outputs[0]

    def brick(self, vector, scale=1.0, width=0.5, height=0.25, mortar=0.02, offset=0.5):
        node = self.new("ShaderNodeTexBrick", offset=offset)
        self.put(node.inputs["Vector"], vector)
        self.put(node.inputs["Scale"], scale)
        self.put(node.inputs["Mortar Size"], mortar)
        self.put(node.inputs["Brick Width"], width)
        self.put(node.inputs["Row Height"], height)
        self.put(node.inputs["Color1"], (1, 1, 1, 1))
        self.put(node.inputs["Color2"], (0.5, 0.5, 0.5, 1))
        self.put(node.inputs["Mortar"], (0, 0, 0, 1))
        return node.outputs["Color"], node.outputs["Fac"]

    # ------------------------------------------------------------------ math
    def math(self, operation, a, b=None, c=None, clamp=False):
        node = self.new("ShaderNodeMath", operation=operation, use_clamp=clamp)
        self.put(node.inputs[0], a)
        if b is not None:
            self.put(node.inputs[1], b)
        if c is not None:
            self.put(node.inputs[2], c)
        return node.outputs[0]

    def add(self, a, b): return self.math("ADD", a, b)
    def sub(self, a, b): return self.math("SUBTRACT", a, b)
    def mul(self, a, b): return self.math("MULTIPLY", a, b)
    def div(self, a, b): return self.math("DIVIDE", a, b)
    def power(self, a, b): return self.math("POWER", a, b)
    def floor(self, a): return self.math("FLOOR", a)
    def fract(self, a): return self.math("FRACT", a)
    def absolute(self, a): return self.math("ABSOLUTE", a)
    def minimum(self, a, b): return self.math("MINIMUM", a, b)
    def maximum(self, a, b): return self.math("MAXIMUM", a, b)
    def sine(self, a): return self.math("SINE", a)
    def less(self, a, b): return self.math("LESS_THAN", a, b)
    def greater(self, a, b): return self.math("GREATER_THAN", a, b)
    def clamp01(self, a): return self.math("ADD", a, 0.0, clamp=True)

    def smooth(self, value, low, high):
        """0 below `low`, 1 above `high`, smooth in between."""
        node = self.new("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        self.put(node.inputs["Value"], value)
        self.put(node.inputs["From Min"], low)
        self.put(node.inputs["From Max"], high)
        return node.outputs[0]

    def remap(self, value, low, high, to_low=0.0, to_high=1.0):
        node = self.new("ShaderNodeMapRange")
        self.put(node.inputs["Value"], value)
        self.put(node.inputs["From Min"], low)
        self.put(node.inputs["From Max"], high)
        self.put(node.inputs["To Min"], to_low)
        self.put(node.inputs["To Max"], to_high)
        return node.outputs[0]

    # ---------------------------------------------------------------- colour
    def ramp(self, factor, stops, interpolation="LINEAR"):
        """stops: [(position, (r, g, b)), ...] in ascending order."""
        node = self.new("ShaderNodeValToRGB")
        ramp = node.color_ramp
        ramp.interpolation = interpolation
        while len(ramp.elements) < len(stops):
            ramp.elements.new(0.5)
        for element, (position, colour) in zip(ramp.elements, stops):
            element.position = position
            element.color = _rgba(colour)
        self.put(node.inputs[0], factor)
        return node.outputs[0]

    def mix(self, factor, a, b, blend="MIX"):
        node = self.new("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_factor=True)
        self.put(self.by_id(node.inputs, "Factor_Float"), factor)
        self.put(self.by_id(node.inputs, "A_Color"), a)
        self.put(self.by_id(node.inputs, "B_Color"), b)
        return self.by_id(node.outputs, "Result_Color")

    def mix_value(self, factor, a, b):
        node = self.new("ShaderNodeMix", data_type="FLOAT", clamp_factor=True)
        self.put(self.by_id(node.inputs, "Factor_Float"), factor)
        self.put(self.by_id(node.inputs, "A_Float"), a)
        self.put(self.by_id(node.inputs, "B_Float"), b)
        return self.by_id(node.outputs, "Result_Float")

    def hsv(self, colour, hue=0.5, saturation=1.0, value=1.0):
        node = self.new("ShaderNodeHueSaturation")
        self.put(node.inputs["Color"], colour)
        self.put(node.inputs["Hue"], hue)
        self.put(node.inputs["Saturation"], saturation)
        self.put(node.inputs["Value"], value)
        return node.outputs[0]

    def ao(self, distance=0.25, samples=8):
        """Ambient occlusion factor (1 open, 0 buried): dirt in corners, wear on open faces."""
        node = self.new("ShaderNodeAmbientOcclusion", samples=samples)
        self.put(node.inputs["Distance"], distance)
        return node.outputs["AO"]

    def bump(self, height, distance=0.01, strength=1.0, normal=None):
        node = self.new("ShaderNodeBump")
        self.put(node.inputs["Height"], height)
        self.put(node.inputs["Distance"], distance)
        self.put(node.inputs["Strength"], strength)
        if normal is not None:
            self.put(node.inputs["Normal"], normal)
        return node.outputs[0]

    # --------------------------------------------------------------- shaders
    def principled(self, base=(0.5, 0.5, 0.5), roughness=0.8, metallic=0.0, bump=None, specular=0.3,
                   emission=None, emission_strength=0.0, alpha=None):
        node = self.new("ShaderNodeBsdfPrincipled")
        self.put(node.inputs["Base Color"], base)
        self.put(node.inputs["Roughness"], roughness)
        self.put(node.inputs["Metallic"], metallic)
        self.put(node.inputs["Specular IOR Level"], specular)
        if bump is not None:
            self.put(node.inputs["Normal"], bump)
        if emission is not None:
            self.put(node.inputs["Emission Color"], emission)
            self.put(node.inputs["Emission Strength"], emission_strength)
        if alpha is not None:
            self.put(node.inputs["Alpha"], alpha)
        self.links.new(node.outputs[0], self.output.inputs["Surface"])
        return node

    def emission(self, colour, strength=1.0):
        node = self.new("ShaderNodeEmission")
        self.put(node.inputs["Color"], colour)
        self.put(node.inputs["Strength"], strength)
        self.links.new(node.outputs[0], self.output.inputs["Surface"])
        return node
