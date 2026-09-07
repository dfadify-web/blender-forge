# -*- coding: utf-8 -*-
"""
bforge - libreria de modelado procedural rapido para Blender 4.x
================================================================
Uso en cualquier script:

    import sys, os
    sys.path.insert(0, os.path.expanduser("~/.claude/skills/blender/lib"))
    from bforge import *

    clear()
    P = palette(piel="#A32BD4", traje="#451676")
    ...
    finish_scene("mi_modelo", OUT_DIR)

Todo se ejecuta headless:
    blender.exe -b --factory-startup --python script.py

Variables de entorno (ver cfg()):
    BF_SAMPLES   muestras de Cycles            (def 64)
    BF_VIEWS     front,34,side,back,orbit,none (def front,34)
    BF_RES       ancho x alto, ej 900x1000     (def 900x1000)
    BF_ENGINE    CYCLES | EEVEE                (def CYCLES)
    BF_GLB       1|0 exportar .glb             (def 1)
    BF_BLEND     1|0 guardar .blend            (def 1)
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Quaternion, Euler, Matrix

M = math.radians
TAU = math.pi * 2

# ============================================================ COLOR / MATERIAL

def srgb(h):
    """'#RRGGBB' -> tupla lineal RGBA lista para Blender."""
    if isinstance(h, (tuple, list)):
        return tuple(h) if len(h) == 4 else tuple(h) + (1.0,)
    h = h.lstrip('#'); o = []
    for i in (0, 2, 4):
        c = int(h[i:i+2], 16) / 255.0
        o.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (o[0], o[1], o[2], 1.0)


def mat(name, col="#CCCCCC", rough=0.45, metal=0.0, emis=None, estr=0.0,
        spec=0.5, alpha=1.0, transmission=0.0):
    """Crea (o reutiliza) un material Principled. Devuelve el material."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = srgb(col)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for key, val in (("Specular IOR Level", spec), ("Alpha", alpha),
                     ("Transmission Weight", transmission)):
        try: b.inputs[key].default_value = val
        except Exception: pass
    if emis:
        b.inputs["Emission Color"].default_value = srgb(emis)
        b.inputs["Emission Strength"].default_value = estr
    if alpha < 1.0 or transmission > 0:
        m.blend_method = 'BLEND'
    m.diffuse_color = srgb(col)
    return m


def palette(**kw):
    """palette(piel='#A32BD4', traje='#451676') -> dict de materiales.
    Valor = hex, o tupla (hex, dict_de_kwargs)."""
    out = {}
    for k, v in kw.items():
        if isinstance(v, (tuple, list)) and len(v) == 2 and isinstance(v[1], dict):
            out[k] = mat(k, v[0], **v[1])
        else:
            out[k] = mat(k, v)
    return out


# ================================================================ ESCENA / UTIL

def clear():
    """Vacia la escena por completo (objetos + datos huerfanos)."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
              bpy.data.lights, bpy.data.armatures, bpy.data.curves):
        for d in list(c):
            if d.users == 0:
                c.remove(d)


def desel():
    bpy.ops.object.select_all(action='DESELECT')


def act(o):
    """Deja o como unico seleccionado + activo (necesario para casi todo op)."""
    desel(); o.select_set(True); bpy.context.view_layer.objects.active = o
    return o


def smooth(o, ang=40):
    """Shade smooth con angulo (auto smooth de 4.1+)."""
    act(o); bpy.ops.object.shade_smooth()
    try: bpy.ops.object.shade_auto_smooth(angle=M(ang))
    except Exception: pass
    return o


def flat(o):
    act(o); bpy.ops.object.shade_flat(); return o


def finish(o, m, name, sm=True, ang=40):
    o.name = name
    if m is not None:
        if o.data.materials: o.data.materials[0] = m
        else: o.data.materials.append(m)
    if sm: smooth(o, ang)
    return o


def apply_tr(o, loc=False, rot=True, scale=True):
    act(o)
    bpy.ops.object.transform_apply(location=loc, rotation=rot, scale=scale)
    return o


def add_mod(o, kind, apply=True, **kw):
    """Anade un modificador y (por defecto) lo aplica."""
    act(o)
    md = o.modifiers.new(kind.lower(), kind)
    for k, v in kw.items():
        setattr(md, k, v)
    if apply:
        bpy.ops.object.modifier_apply(modifier=md.name)
        return o
    return md


def bevel(o, width=0.02, segments=3, angle=35):
    return add_mod(o, 'BEVEL', width=width, segments=segments,
                   limit_method='ANGLE', angle_limit=M(angle))


def subsurf(o, levels=1):
    return add_mod(o, 'SUBSURF', levels=levels, render_levels=levels)


def solidify(o, thickness=0.05, offset=0.0):
    return add_mod(o, 'SOLIDIFY', thickness=thickness, offset=offset)


def decimate(o, ratio=0.5):
    return add_mod(o, 'DECIMATE', ratio=ratio)


def array(o, count=3, offset=(1, 0, 0)):
    return add_mod(o, 'ARRAY', count=count, use_relative_offset=False,
                   use_constant_offset=True, constant_offset_displace=offset)


def mirror_x(o):
    return add_mod(o, 'MIRROR', use_axis=(True, False, False))


# ==================================================================== PRIMITIVAS

def sphere(name="Sphere", loc=(0, 0, 0), r=1.0, sc=(1, 1, 1), rot=(0, 0, 0),
           m=None, seg=48, ring=24, sm=True):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=ring,
                                         radius=r, location=loc)
    o = bpy.context.object; o.scale = sc; o.rotation_euler = rot; apply_tr(o)
    return finish(o, m, name, sm=sm)


def box(name="Box", loc=(0, 0, 0), sc=(1, 1, 1), rot=(0, 0, 0), m=None,
        bev=0.0, segs=4, sm=True):
    """sc = SEMI-ejes (media anchura), como en un cubo de size=2."""
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=loc)
    o = bpy.context.object; o.scale = sc; o.rotation_euler = rot; apply_tr(o)
    if bev > 0:
        bevel(o, bev, segs)
    return finish(o, m, name, sm=sm)


def cyl(name="Cyl", loc=(0, 0, 0), r=1.0, d=1.0, rot=(0, 0, 0), m=None,
        v=32, bev=0.0, sc=(1, 1, 1), sm=True):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=loc)
    o = bpy.context.object; o.scale = sc; o.rotation_euler = rot; apply_tr(o)
    if bev > 0:
        bevel(o, bev, 3)
    return finish(o, m, name, sm=sm)


def cone(name="Cone", loc=(0, 0, 0), r1=1.0, r2=0.0, d=2.0, rot=(0, 0, 0),
         m=None, v=32, sc=(1, 1, 1), sm=True):
    bpy.ops.mesh.primitive_cone_add(vertices=v, radius1=r1, radius2=r2,
                                    depth=d, location=loc)
    o = bpy.context.object; o.scale = sc; o.rotation_euler = rot; apply_tr(o)
    return finish(o, m, name, sm=sm)


def torus(name="Torus", loc=(0, 0, 0), maj=1.0, minr=0.1, rot=(0, 0, 0),
          m=None, ms=48, mns=16):
    bpy.ops.mesh.primitive_torus_add(location=loc, rotation=rot,
                                     major_radius=maj, minor_radius=minr,
                                     major_segments=ms, minor_segments=mns)
    return finish(bpy.context.object, m, name)


def plane(name="Plane", loc=(0, 0, 0), size=10.0, rot=(0, 0, 0), m=None):
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc, rotation=rot)
    return finish(bpy.context.object, m, name, sm=False)


def capsule(name="Capsule", p1=(0, 0, 0), p2=(0, 0, 1), r=0.2, m=None, v=32):
    """Capsula entre dos puntos: ideal para brazos, piernas, ramas, tuberias."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1; L = max(d.length, 1e-5); mid = (p1 + p2) / 2
    rot = d.to_track_quat('Z', 'Y').to_euler()
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=L,
                                        location=mid, rotation=rot)
    body = bpy.context.object
    a = sphere(name + "_a", tuple(p1), r, seg=v, ring=max(8, v // 2))
    b = sphere(name + "_b", tuple(p2), r, seg=v, ring=max(8, v // 2))
    desel()
    for o in (body, a, b): o.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join(); o = bpy.context.object
    add_mod(o, 'WELD', merge_threshold=0.0005)
    return finish(o, m, name)


def star(name="Star", loc=(0, 0, 0), ro=0.1, ri=0.045, depth=0.03,
         rot=(0, 0, 0), m=None, points=5):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); vs = []
    for i in range(points * 2):
        a = math.pi / 2 + i * math.pi / points
        r = ro if i % 2 == 0 else ri
        vs.append(bm.verts.new((r * math.cos(a), r * math.sin(a), 0)))
    bm.faces.new(vs); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    solidify(o, depth)
    return finish(o, m, name, sm=False)


def poly_prism(name="Prism", loc=(0, 0, 0), r=1.0, h=1.0, sides=6, rot=(0, 0, 0), m=None):
    return cyl(name, loc, r, h, rot, m, v=sides, sm=False)


def text3d(name="Text", body="TEXT", loc=(0, 0, 0), size=1.0, extrude=0.05,
           rot=(0, 0, 0), m=None, align='CENTER'):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.data.body = body; o.data.size = size; o.data.extrude = extrude
    o.data.align_x = align; o.data.align_y = 'CENTER'
    act(o); bpy.ops.object.convert(target='MESH')
    return finish(bpy.context.object, m, name, sm=False)


# ==================================================================== BOOLEANAS

def boolean(target, cutter, op='DIFFERENCE', delete=True):
    act(target)
    md = target.modifiers.new("bool", 'BOOLEAN')
    md.operation = op; md.object = cutter; md.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=md.name)
    if delete:
        bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def cut(target, cutter):     return boolean(target, cutter, 'DIFFERENCE')
def inter(target, cutter):   return boolean(target, cutter, 'INTERSECT')
def union(target, cutter):   return boolean(target, cutter, 'UNION')


def join(objs, name=None, m=None):
    objs = [o for o in objs if o and o.name in bpy.data.objects]
    if not objs: return None
    desel()
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.object
    if name: o.name = name
    if m: finish(o, m, o.name)
    return o


# ================================================ SUPERFICIES ESFERICAS (CARAS)

class Ball:
    """Bloque esferico (cabeza, planeta, casco, cupula) con detalles que se
    pegan de verdad a la superficie.

    b = Ball(center=(0,0,2.7), r=0.95, squash=(1,0.94,1))
    b.skin("Cabeza", MAT_PIEL)                     # la esfera base
    b.patch("Ojo", 0.28, -0.19, 0.27, 0.25, NEGRO) # detalle conformado
    b.shell("Casco", 1.055, 1.018, MAT_CASCO)      # cascara
    b.cut_cone(casco, dz=-0.32, hax=45, haz=52)    # abrir la cara
    b.done()                                       # aplica el squash a todo

    TRUCO CLAVE: todo se construye sobre una ESFERA PERFECTA y el aplastado
    (squash) se aplica al final via empty padre; asi los detalles nunca flotan.
    """

    def __init__(self, center=(0, 0, 0), r=1.0, squash=(1, 1, 1), name="Ball"):
        self.c = Vector(center); self.r = r
        self.squash = squash; self.name = name
        self.parts = []
        self.empty = None

    # --- helpers de coordenadas
    def at(self, x=0.0, y=0.0, z=0.0):
        return (self.c.x + x, self.c.y + y, self.c.z + z)

    def add(self, o):
        if o: self.parts.append(o)
        return o

    # --- piezas
    def skin(self, name="Skin", m=None, seg=96, ring=48, taper=0.0, taper_from=0.40):
        """Esfera base. taper afina la parte inferior (menton)."""
        o = sphere(name, tuple(self.c), self.r, m=m, seg=seg, ring=ring)
        if taper:
            for v in o.data.vertices:            # OJO: coords LOCALES
                t = max(0.0, (-v.co.z - taper_from * self.r) / (self.r - taper_from * self.r))
                if t > 0:
                    f = 1.0 - taper * (min(t, 1.0) ** 1.7)
                    v.co.x *= f; v.co.y *= f
        return self.add(o)

    def shell(self, name, k_out, k_in, m=None, seg=128, ring=64, keep=True):
        """Cascara esferica entre dos radios (k = multiplo de r)."""
        o = sphere(name, tuple(self.c), self.r * k_out, m=m, seg=seg, ring=ring)
        inn = sphere(name + "_in", tuple(self.c), self.r * k_in, seg=seg, ring=ring)
        cut(o, inn)
        return self.add(o) if keep else o

    def solid(self, name, k, m=None, seg=96, ring=48, keep=False):
        o = sphere(name, tuple(self.c), self.r * k, m=m, seg=seg, ring=ring)
        return self.add(o) if keep else o

    def patch(self, name, px, pz, hx, hz, m=None, k=1.048, roll=0.0,
              shape='ellipse', seg=64, ring=32, depth=3.0, keep=True):
        """Detalle pegado a la superficie: esfera(k) ∩ cilindro orientado hacia
        el centro. px,pz = punto sobre la esfera (y se deduce). hx,hz = semiejes.
        roll gira el sello sobre la normal (cejas inclinadas, etc)."""
        yy = math.sqrt(max(self.r ** 2 - px * px - pz * pz, 1e-4))
        d = Vector((px, -yy, pz)).normalized()
        q = d.to_track_quat('Z', 'Y') @ Quaternion(Vector((0, 0, 1)), roll)
        # el sello arranca justo detras del centro y va SOLO hacia delante,
        # si no aparece un detalle duplicado en la nuca
        loc = self.c + d * (depth / 2.0 - 0.15 * self.r)
        if shape == 'ellipse':
            bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1.0,
                                                depth=depth, location=loc)
        else:
            bpy.ops.mesh.primitive_cube_add(size=2.0, location=loc)
        cutr = bpy.context.object
        cutr.scale = (hx, hz, 1.0 if shape == 'ellipse' else depth / 2)
        cutr.rotation_mode = 'QUATERNION'; cutr.rotation_quaternion = q
        apply_tr(cutr)
        o = sphere(name, tuple(self.c), self.r * k, m=m, seg=seg, ring=ring)
        inter(o, cutr); smooth(o, 34)
        return self.add(o) if keep else o

    # --- cortadores
    def cone_cutter(self, name="cone", dz=-0.30, hax=45.0, haz=52.0, D=None):
        """Cono con vertice en el centro: abre un hueco cuyo borde ENVUELVE la
        curvatura (visera de casco, boca de cueva). hax/haz en grados."""
        D = D or self.r * 3.5
        d = Vector((0.0, -1.0, dz)).normalized()
        q = (-d).to_track_quat('Z', 'Y')
        loc = self.c + d * (D / 2.0)
        bpy.ops.mesh.primitive_cone_add(vertices=96, radius1=1.0, radius2=0.0,
                                        depth=D, location=loc)
        o = bpy.context.object
        o.scale = (math.tan(M(hax)) * D, math.tan(M(haz)) * D, 1.0)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = q
        apply_tr(o); o.name = name
        return o

    def zslab(self, name="slab", z0=-1, z1=1, big=None):
        big = big or self.r * 3
        return box(name, self.at(0, 0, (z0 + z1) / 2), (big, big, (z1 - z0) / 2))

    def frontcut(self, name="fc", ymax=-0.02, big=None):
        big = big or self.r * 3
        return box(name, self.at(0, ymax - big, 0), (big, big, big))

    def ellip_cyl(self, name="ec", cx=0.0, cz=0.0, hx=1.0, hz=1.0,
                  yback=0.10, L=None):
        """Cilindro eliptico con eje en Y, solo mitad frontal (y < yback)."""
        L = L or self.r * 3.2
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1.0, depth=L,
                                            location=self.at(cx, yback - L / 2, cz))
        o = bpy.context.object
        o.scale = (hx, hz, 1.0); o.rotation_euler = (M(90), 0, 0)
        apply_tr(o); o.name = name
        return o

    def band(self, name, k_out, k_in, m, region, front=-0.02, seg=128, ring=64):
        """Banda curva sobre la esfera (gafas, cinturon, anillo planetario).
        region = objeto cortador (usa ellip_cyl o zslab)."""
        o = self.shell(name, k_out, k_in, m, seg, ring, keep=False)
        inter(o, region)
        inter(o, self.frontcut(name + "_f", front))
        smooth(o, 30)
        return self.add(o)

    def done(self, parent=None):
        """Crea el empty, cuelga todas las piezas y aplica el aplastado."""
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=tuple(self.c))
        e = bpy.context.object; e.name = self.name + "_RIG"
        for o in self.parts:
            if o and o.name in bpy.data.objects:
                o.parent = e
                o.matrix_parent_inverse = e.matrix_world.inverted()
        e.scale = self.squash
        if parent:
            e.parent = parent
            e.matrix_parent_inverse = parent.matrix_world.inverted()
        self.empty = e
        return e


# ================================================================= RUIDO / MAPA

def _hash2(x, y, seed=0):
    n = int(x) * 374761393 + int(y) * 668265263 + int(seed) * 1442695041
    n = (n ^ (n >> 13)) * 1274126177
    n ^= (n >> 16)
    return (n & 0xFFFFFF) / float(0xFFFFFF)


def _smooth(t):
    return t * t * (3 - 2 * t)


def noise2(x, y, seed=0):
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    u, v = _smooth(xf), _smooth(yf)
    a = _hash2(xi, yi, seed);       b = _hash2(xi + 1, yi, seed)
    c = _hash2(xi, yi + 1, seed);   d = _hash2(xi + 1, yi + 1, seed)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def fbm(x, y, seed=0, octaves=4, lac=2.0, gain=0.5):
    amp, freq, s, norm = 1.0, 1.0, 0.0, 0.0
    for _ in range(octaves):
        s += amp * noise2(x * freq, y * freq, seed + int(freq))
        norm += amp; amp *= gain; freq *= lac
    return s / max(norm, 1e-6)


def terrain(name="Terreno", size=40.0, res=80, height=3.0, scale=0.12, seed=1,
            octaves=4, m=None, island=0.0, flat_shade=True, ridged=False):
    """Malla de terreno por ruido fBm.
    island>0 hunde los bordes (0.6 = isla clara). ridged = crestas montanosas."""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=res, y_subdivisions=res,
                                    size=size, location=(0, 0, 0))
    o = bpy.context.object; o.name = name
    half = size / 2.0
    for v in o.data.vertices:
        n = fbm(v.co.x * scale, v.co.y * scale, seed, octaves)
        if ridged:
            n = 1.0 - abs(n * 2 - 1)
        z = n * height
        if island > 0:
            d = math.sqrt(v.co.x ** 2 + v.co.y ** 2) / half
            z -= island * height * max(0.0, d - 0.45) ** 2 * 6.0
        v.co.z = z
    o.data.update()
    finish(o, m, name, sm=not flat_shade)
    if flat_shade: flat(o)
    return o


def flatten_disc(o, center=(0, 0), radius=8.0, z=0.0, blend=3.0):
    """Aplana un disco del terreno (plazas, arenas, campos de juego)."""
    cx, cy = center
    for v in o.data.vertices:
        d = math.sqrt((v.co.x - cx) ** 2 + (v.co.y - cy) ** 2)
        if d < radius + blend:
            t = 1.0 if d <= radius else 1.0 - _smooth((d - radius) / blend)
            v.co.z = v.co.z * (1 - t) + z * t
    o.data.update()
    return o


def sample_terrain(o, x, y):
    """Altura del terreno en (x,y) - raycast local. Devuelve z (0 si falla)."""
    mw = o.matrix_world.inverted()
    origin = mw @ Vector((x, y, 1000.0))
    hit, loc, nor, idx = o.ray_cast(origin, Vector((0, 0, -1)))
    return (o.matrix_world @ loc).z if hit else 0.0


def water(name="Agua", size=60.0, z=0.0, m=None):
    return plane(name, (0, 0, z), size, m=m)


def tilemap(rows, builders, tile=2.0, origin=(0, 0, 0), center=True):
    """Construye un mapa desde un dibujo ASCII.

        MAPA = ["#####",
                "#..o#",
                "#.@.#",
                "#####"]
        tilemap(MAPA, {'#': muro, '.': suelo, 'o': caja, '@': spawn})

    Cada builder recibe (x, y, z, i, j) y devuelve objeto(s) o None.
    Fila 0 = arriba (-Y crece hacia abajo en pantalla)."""
    out = []
    h = len(rows); w = max(len(r) for r in rows)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            b = builders.get(ch)
            if not b:
                continue
            x = origin[0] + ((i - (w - 1) / 2.0) if center else i) * tile
            y = origin[1] - ((j - (h - 1) / 2.0) if center else j) * tile
            r = b(x, y, origin[2], i, j)
            if r:
                out.extend(r if isinstance(r, (list, tuple)) else [r])
    return out


def scatter(builder, n=20, area=(-10, 10, -10, 10), seed=7, zfn=None,
            scale=(0.8, 1.3), rot_z=True, min_dist=0.0):
    """Reparte n instancias. builder(x, y, z, i) -> objeto(s)."""
    out, placed = [], []
    x0, x1, y0, y1 = area
    i = 0; guard = 0
    while i < n and guard < n * 40:
        guard += 1
        rx = x0 + _hash2(guard, i, seed) * (x1 - x0)
        ry = y0 + _hash2(i, guard, seed + 99) * (y1 - y0)
        if min_dist > 0 and any((rx - px) ** 2 + (ry - py) ** 2 < min_dist ** 2
                                for px, py in placed):
            continue
        z = zfn(rx, ry) if zfn else 0.0
        r = builder(rx, ry, z, i)
        if r:
            objs = r if isinstance(r, (list, tuple)) else [r]
            s = scale[0] + _hash2(i, guard, seed + 7) * (scale[1] - scale[0])
            for o in objs:
                o.scale = (o.scale[0] * s, o.scale[1] * s, o.scale[2] * s)
                if rot_z:
                    o.rotation_euler[2] = _hash2(guard, i, seed + 3) * TAU
            out.extend(objs)
        placed.append((rx, ry)); i += 1
    return out


def radial(builder, n=8, radius=5.0, z=0.0, phase=0.0):
    out = []
    for i in range(n):
        a = phase + i * TAU / n
        r = builder(math.cos(a) * radius, math.sin(a) * radius, z, i)
        if r:
            out.extend(r if isinstance(r, (list, tuple)) else [r])
    return out


# =============================================================== ASSETS RAPIDOS

def tree(loc=(0, 0, 0), h=3.0, m_trunk=None, m_leaf=None, style='cone', seed=0):
    x, y, z = loc
    t = cyl("Tronco", (x, y, z + h * 0.25), h * 0.07, h * 0.5, m=m_trunk, v=8, sm=False)
    parts = [t]
    if style == 'cone':
        for i in range(3):
            k = 1 - i * 0.28
            parts.append(cone("Copa%d" % i, (x, y, z + h * (0.5 + i * 0.22)),
                              h * 0.30 * k, 0.0, h * 0.42 * k, m=m_leaf, v=8, sm=False))
    else:
        parts.append(sphere("Copa", (x, y, z + h * 0.75), h * 0.32,
                            (1, 1, 0.85), m=m_leaf, seg=12, ring=8, sm=False))
    return parts


def rock(loc=(0, 0, 0), r=0.5, m=None, seed=0):
    o = sphere("Roca", loc, r, seg=10, ring=6, sm=False)
    for i, v in enumerate(o.data.vertices):
        f = 0.72 + _hash2(i, seed, seed) * 0.55
        v.co *= f
    o.data.update(); flat(o)
    return finish(o, m, "Roca", sm=False)


def crystal(loc=(0, 0, 0), h=1.0, r=0.22, m=None, tilt=8):
    o = cone("Cristal", (loc[0], loc[1], loc[2] + h / 2), r, r * 0.25, h,
             (M(tilt), 0, 0), m, v=6, sm=False)
    return o


def platform(loc=(0, 0, 0), sc=(1, 1, 0.15), m=None, bev=0.06, m_top=None):
    p = box("Plataforma", loc, sc, m=m, bev=bev, segs=3)
    out = [p]
    if m_top:
        out.append(box("PlatTop", (loc[0], loc[1], loc[2] + sc[2]),
                       (sc[0] * 0.94, sc[1] * 0.94, 0.02), m=m_top, bev=0.01))
    return out


def building(loc=(0, 0, 0), w=2.0, d=2.0, h=4.0, m=None, m_win=None,
             floors=3, roof=True, m_roof=None):
    x, y, z = loc
    parts = [box("Edificio", (x, y, z + h / 2), (w, d, h / 2), m=m, bev=0.05)]
    if m_win:
        for f in range(floors):
            fz = z + h * (f + 0.6) / (floors + 0.2)
            for sgn, ax in ((-1, 'y'), (1, 'y')):
                parts.append(box("Win", (x, y + sgn * (d + 0.01), fz),
                                 (w * 0.62, 0.02, h * 0.09), m=m_win, sm=False))
            for sgn in (-1, 1):
                parts.append(box("Win", (x + sgn * (w + 0.01), y, fz),
                                 (0.02, d * 0.62, h * 0.09), m=m_win, sm=False))
    if roof:
        parts.append(box("Tejado", (x, y, z + h + 0.08), (w * 1.06, d * 1.06, 0.09),
                         m=m_roof or m, bev=0.03))
    return parts


def road(p0, p1, width=1.2, z=0.02, m=None):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0; L = d.length
    ang = math.atan2(d.y, d.x)
    return box("Camino", tuple((p0 + p1) / 2 + Vector((0, 0, z))),
               (L / 2, width / 2, 0.01), (0, 0, ang), m=m, sm=False)


def fence(p0, p1, n=6, h=0.7, m=None):
    p0, p1 = Vector(p0), Vector(p1); out = []
    for i in range(n + 1):
        p = p0.lerp(p1, i / n)
        out.append(box("Poste", (p.x, p.y, p.z + h / 2), (0.05, 0.05, h / 2), m=m, sm=False))
    return out


# ============================================================== RIG RAPIDO (opc)

def quick_rig(objs, spine=(0, 0, 1.0), head=(0, 0, 2.2), hips=(0, 0, 0.9),
              arm_y=0.5, leg_y=0.25, name="RIG"):
    """Armature minima (root/hips/spine/head/brazos/piernas) + auto weights.
    Suficiente para posar rapido o exportar a un motor."""
    bpy.ops.object.armature_add(location=(0, 0, 0))
    arm = bpy.context.object; arm.name = name
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    root = eb[0]; root.name = "root"; root.head = (0, 0, 0); root.tail = (0, 0, 0.3)

    def bone(nm, h, t, parent=None):
        b = eb.new(nm); b.head = h; b.tail = t
        if parent: b.parent = parent; b.use_connect = False
        return b

    hip = bone("hips", hips, spine, root)
    sp = bone("spine", spine, head, hip)
    bone("head", head, (head[0], head[1], head[2] + 0.5), sp)
    for s, sfx in ((-1, "L"), (1, "R")):
        bone("arm_" + sfx, (s * arm_y * 0.6, 0, spine[2] + 0.15),
             (s * arm_y * 1.6, 0, spine[2] - 0.5), sp)
        bone("leg_" + sfx, (s * leg_y, 0, hips[2]), (s * leg_y, 0, 0.05), hip)
    bpy.ops.object.mode_set(mode='OBJECT')
    desel()
    for o in objs:
        if o and o.type == 'MESH': o.select_set(True)
    arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    return arm


# ============================================================ LUCES / RENDER

def cfg():
    return {
        "samples": int(os.environ.get("BF_SAMPLES", "64")),
        "views": [v for v in os.environ.get("BF_VIEWS", "front,34").split(",") if v],
        "res": os.environ.get("BF_RES", "900x1000"),
        "engine": os.environ.get("BF_ENGINE", "CYCLES").upper(),
        "glb": os.environ.get("BF_GLB", "1") == "1",
        "blend": os.environ.get("BF_BLEND", "1") == "1",
    }


def setup_render(engine=None, samples=None, res=None, exposure=0.0, transparent=False):
    c = cfg()
    sc = bpy.context.scene
    eng = (engine or c["engine"]).upper()
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if eng.startswith("EEVEE") else 'CYCLES'
    if sc.render.engine == 'CYCLES':
        sc.cycles.device = 'CPU'
        sc.cycles.samples = samples or c["samples"]
        sc.cycles.use_denoising = True
    else:
        sc.eevee.taa_render_samples = samples or c["samples"]
    w, h = (res or c["res"]).lower().split("x")
    sc.render.resolution_x = int(w); sc.render.resolution_y = int(h)
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = exposure
    return sc


def world_color(col="#DFE6EF", strength=0.85):
    w = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
    bpy.context.scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = srgb(col)
    bg.inputs[1].default_value = strength
    return w


def light(name, kind='AREA', loc=(0, 0, 5), energy=500, size=5.0,
          target=(0, 0, 1), color="#FFFFFF", angle=None):
    bpy.ops.object.light_add(type=kind, location=loc)
    l = bpy.context.object; l.name = name
    l.data.energy = energy; l.data.color = srgb(color)[:3]
    if kind == 'AREA': l.data.size = size
    if kind == 'SUN' and angle is not None: l.data.angle = M(angle)
    d = Vector(target) - Vector(loc)
    l.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return l


def studio(target=(0, 0, 1.9), bg="#DFE6EF", strength=0.85, key=620, fill=200,
           rim=330, floor=True, floor_col="#E6EBF2", scale=1.0):
    """Iluminacion de 3 puntos para fichas de personaje/prop."""
    world_color(bg, strength)
    s = scale
    light("Key", 'AREA', (-4.2 * s, -5.0 * s, 6.0 * s), key, 6 * s, target)
    light("Fill", 'AREA', (5.2 * s, -4.2 * s, 3.0 * s), fill, 6 * s, target, "#CFE2FF")
    light("Rim", 'AREA', (1.5 * s, 6.0 * s, 5.0 * s), rim, 5 * s, target, "#E7C9FF")
    light("Bounce", 'AREA', (0, -3.2 * s, 0.2), fill * 0.45, 6 * s, (0, 0, 1.0 * s))
    if floor:
        plane("Suelo", (0, 0, -0.001), 60 * s, m=mat("Suelo", floor_col, 0.7))


def outdoor(sun=4.0, sky="#9FC6F0", strength=1.1, angle=25, rot=35, target=(0, 0, 0)):
    """Luz de exterior para mapas y mundos: sol + cielo."""
    world_color(sky, strength)
    l = light("Sol", 'SUN', (18, -22, 24), sun, target=target, color="#FFF4E0", angle=angle)
    l.rotation_euler = Euler((M(48), 0, M(rot)))
    light("SkyFill", 'AREA', (-16, 14, 18), 260, 30, target, "#BBD8FF")
    return l


def camera(lens=60, name="Cam"):
    bpy.ops.object.camera_add(location=(0, -10, 2))
    c = bpy.context.object; c.name = name; c.data.lens = lens
    bpy.context.scene.camera = c
    return c


def aim(cam, loc, target=(0, 0, 1)):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return cam


def shot(cam, path, loc, target=(0, 0, 1), ortho=None, lens=None):
    aim(cam, loc, target)
    if ortho:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
    else:
        cam.data.type = 'PERSP'
        if lens: cam.data.lens = lens
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def sheet(cam, out_dir, base, target=(0, 0, 1.9), ortho=4.4, dist=12.0, views=None):
    """Ficha de 4 vistas (front/34/side/back), como una reference sheet."""
    views = views or cfg()["views"]
    tz = target[2]
    done = []
    if "front" in views:
        done.append(shot(cam, os.path.join(out_dir, base + "_front.png"),
                         (0, -dist, tz), target, ortho))
    if "34" in views:
        done.append(shot(cam, os.path.join(out_dir, base + "_34.png"),
                         (-dist * 0.42, -dist * 0.72, tz + dist * 0.12), target, None, 85))
    if "side" in views:
        done.append(shot(cam, os.path.join(out_dir, base + "_side.png"),
                         (-dist, 0, tz), target, ortho))
    if "back" in views:
        done.append(shot(cam, os.path.join(out_dir, base + "_back.png"),
                         (0, dist, tz), target, ortho))
    return done


def orbit(cam, out_dir, base, n=8, radius=14.0, height=6.0, target=(0, 0, 1)):
    outs = []
    for i in range(n):
        a = i * TAU / n
        outs.append(shot(cam, os.path.join(out_dir, "%s_orb%02d.png" % (base, i)),
                         (math.cos(a) * radius, math.sin(a) * radius, height), target))
    return outs


# ================================================================ IO / SALIDA

def save_blend(path):
    bpy.ops.wm.save_as_mainfile(filepath=path)
    return path


def export_glb(path, selected=False):
    try:
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                                  use_selection=selected)
        return path
    except Exception as e:
        print("glb export skip:", e)
        return None


def append_blend(path, names=None, kind='Object'):
    """Trae objetos de otro .blend (reutiliza personajes en mapas)."""
    got = []
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        avail = list(getattr(src, kind.lower() + "s"))
        pick = [n for n in avail if (names is None or n in names)]
        setattr(dst, kind.lower() + "s", pick)
    for o in bpy.data.objects:
        if o.users_collection == ():
            bpy.context.collection.objects.link(o); got.append(o)
    return got


def group(name, objs):
    """Empty padre para mover/escalar todo un conjunto de golpe."""
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    e = bpy.context.object; e.name = name
    for o in objs:
        if o and o.name in bpy.data.objects and o.parent is None:
            o.parent = e
            o.matrix_parent_inverse = e.matrix_world.inverted()
    return e


def finish_scene(base, out_dir, cam=None, target=(0, 0, 1.9), ortho=4.4,
                 dist=12.0, glb=None, blend=None):
    """Guarda .blend, renderiza las vistas pedidas y exporta .glb."""
    c = cfg()
    os.makedirs(out_dir, exist_ok=True)
    if (c["blend"] if blend is None else blend):
        save_blend(os.path.join(out_dir, base + ".blend"))
    if cam and c["views"] and c["views"] != ["none"]:
        if "orbit" in c["views"]:
            orbit(cam, out_dir, base, target=target, radius=dist, height=dist * 0.45)
        else:
            sheet(cam, out_dir, base, target, ortho, dist)
    if (c["glb"] if glb is None else glb):
        export_glb(os.path.join(out_dir, base + ".glb"))
    print("BFORGE OK ->", out_dir)
    return out_dir
