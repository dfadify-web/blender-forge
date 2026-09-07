# -*- coding: utf-8 -*-
"""PLANTILLA: mapa / mundo low-poly (terreno + tilemap ASCII + props).
Ejecutar:  BF_SAMPLES=48 BF_VIEWS=34 blender.exe -b --factory-startup --python este.py
"""
import sys, os
for _p in (os.environ.get("BFORGE_LIB"),
           os.path.expanduser("~/.claude/skills/blender/lib"),
           os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")):
    if _p and os.path.isdir(_p):
        sys.path.insert(0, _p); break
from bforge import *

OUT  = os.path.join(os.path.expanduser("~"), "Desktop", "mundo")
NAME = "mundo"

SIZE, TILE = 44.0, 2.4

clear()
P = palette(
    hierba = ("#5FBF63", dict(rough=.85)),
    tierra = ("#8A6A46", dict(rough=.9)),
    piedra = ("#9AA0AA", dict(rough=.8)),
    agua   = ("#2F9BD8", dict(rough=.08, metal=.1)),
    tronco = ("#6B4A2F", dict(rough=.9)),
    hoja   = ("#3E9B52", dict(rough=.85)),
    muro   = ("#B9AE9B", dict(rough=.8)),
    tejado = ("#C25B4B", dict(rough=.75)),
    vidrio = ("#8FD9F5", dict(rough=.1, emis="#8FD9F5", estr=.4)),
    neon   = ("#FF3C9E", dict(emis="#FF3C9E", estr=2.0)),
)

# ==================================================================== TERRENO
suelo = terrain("Terreno", size=SIZE, res=90, height=2.6, scale=0.10,
                seed=7, octaves=4, island=0.55, m=P['hierba'])
mar = water("Mar", size=SIZE * 1.8, z=-0.35, m=P['agua'])
Z = lambda x, y: sample_terrain(suelo, x, y)

# ============================================================== MAPA ASCII
#  # muro   . suelo   T arbol   R roca   C casa   * farola
MAPA = [
    "..#####..",
    ".#..C..#.",
    "#..T.R..#",
    "#.C...C.#",
    "#..R.T..#",
    ".#..*..#.",
    "..#####..",
]

def _muro(x, y, z, i, j):
    return box("Muro", (x, y, Z(x, y) + 0.45), (TILE/2, TILE/2, 0.45),
               m=P['piedra'], bev=0.06)

def _casa(x, y, z, i, j):
    return building((x, y, Z(x, y)), 0.85, 0.85, 2.4, P['muro'], P['vidrio'],
                    floors=2, m_roof=P['tejado'])

def _arbol(x, y, z, i, j):
    return tree((x, y, Z(x, y)), 3.2, P['tronco'], P['hoja'])

def _roca(x, y, z, i, j):
    return rock((x, y, Z(x, y) + 0.3), 0.55, P['piedra'], seed=i * 7 + j)

def _farola(x, y, z, i, j):
    zz = Z(x, y)
    return [cyl("Poste", (x, y, zz + 1.2), 0.07, 2.4, m=P['piedra']),
            sphere("Luz", (x, y, zz + 2.5), 0.18, m=P['neon'])]

tiles = tilemap(MAPA, {'#': _muro, 'C': _casa, 'T': _arbol, 'R': _roca, '*': _farola},
                tile=TILE)

# ============================================ VEGETACION DISPERSA (fuera del mapa)
props = scatter(lambda x, y, z, i: tree((x, y, z), 2.6, P['tronco'], P['hoja']),
                n=26, area=(-SIZE/2 + 3, SIZE/2 - 3, -SIZE/2 + 3, SIZE/2 - 3),
                seed=13, zfn=Z, min_dist=3.4)
props += scatter(lambda x, y, z, i: rock((x, y, z + 0.2), 0.4, P['piedra'], seed=i),
                 n=18, area=(-SIZE/2 + 2, SIZE/2 - 2, -SIZE/2 + 2, SIZE/2 - 2),
                 seed=31, zfn=Z, min_dist=2.0)

group(NAME.upper(), [suelo, mar] + tiles + props)

# ===================================================================== SALIDA
setup_render()
outdoor(sun=4.0, sky="#9FC6F0", strength=1.15)
cam = camera(50)
os.makedirs(OUT, exist_ok=True)
shot(cam, os.path.join(OUT, NAME + "_aerea.png"), (26, -30, 22), (0, 0, 1))
shot(cam, os.path.join(OUT, NAME + "_suelo.png"), (10, -14, 4.5), (0, 0, 2))
finish_scene(NAME, OUT, cam=None)   # cam=None: ya hemos hecho los shots a mano
