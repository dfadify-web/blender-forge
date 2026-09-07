# -*- coding: utf-8 -*-
"""PLANTILLA: personaje chibi. Copiar, renombrar y tocar solo las constantes.
Ejecutar:  BF_SAMPLES=48 BF_VIEWS=front,34 blender.exe -b --factory-startup --python este.py
"""
import sys, os
for _p in (os.environ.get("BFORGE_LIB"),
           os.path.expanduser("~/.claude/skills/blender/lib"),
           os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")):
    if _p and os.path.isdir(_p):
        sys.path.insert(0, _p); break
from bforge import *

OUT  = os.path.join(os.path.expanduser("~"), "Desktop", "personaje")
NAME = "personaje"

# --------------------------------------------------------------- PROPORCIONES
# medidas en fracciones de la referencia -> altura total ~3.9
HR, HZ, HSQ = 0.95, 2.70, 0.94      # radio cabeza, altura del centro, aplastado Y
TZ, TW, TD, TH = 1.36, 0.535, 0.360, 0.470   # torso: centro y semiejes
EX, EZ = 0.278, -0.195              # centro de los ojos sobre la esfera

clear()
P = palette(
    piel   = "#A32BD4",
    casco  = "#59189B",
    oscuro = "#3B1069",
    traje  = "#451676",
    claro  = ("#A464DC", dict(rough=.46)),
    pant   = "#8E1FC6",
    visor  = ("#3ED3EC", dict(rough=.12, emis="#3ED3EC", estr=.35)),
    metal  = ("#C6C8D6", dict(rough=.34, metal=.2)),
    gris   = ("#9EA0B0", dict(rough=.42, metal=.15)),
    negro  = ("#0C0910", dict(rough=.30)),
    blanco = "#FFFFFF",
)

# ==================================================================== CABEZA
b = Ball(center=(0, 0, HZ), r=HR, squash=(1, HSQ, 1), name="Cabeza")
b.skin("Cabeza", P['piel'], taper=0.11)

for s in (-1, 1):                                    # ojos + brillos + cejas
    b.patch("Ojo_%d" % s, s*EX, EZ, 0.284, 0.256, P['negro'], k=1.045, roll=M(s*9))
    b.patch("BrilloA_%d" % s, s*EX-0.078, EZ+0.088, 0.078, 0.078, P['blanco'], k=1.058)
    b.patch("BrilloB_%d" % s, s*EX-0.118, EZ-0.112, 0.045, 0.045, P['blanco'], k=1.058)
    b.patch("Ceja_%d" % s, s*0.265, 0.098, 0.218, 0.056, P['negro'], k=1.047, roll=M(s*27))
b.patch("Boca", 0.0, -0.545, 0.100, 0.021, P['negro'], k=1.045)

casco = b.shell("Casco", 1.055, 1.018, P['casco'])   # cascara + apertura de cara
cut(casco, b.cone_cutter("cara", dz=-0.32, hax=45, haz=52))
cut(casco, b.zslab("bajo", -2.2, -0.800))
smooth(casco, 30)

b.band("Gafas_Marco", 1.108, 1.040, P['oscuro'],     # marco
       b.ellip_cyl("r1", cz=0.512, hx=1.80, hz=0.250), front=-0.150)
b.band("Gafas_Lente", 1.098, 1.045, P['visor'],      # lente
       b.ellip_cyl("r2", cz=0.508, hx=1.655, hz=0.172), front=-0.220)

for s in (-1, 1):                                    # orejeras
    b.add(cyl("Orejera_%d" % s, b.at(s*0.880, -0.075, -0.215), 0.252, 0.250,
              (0, M(90), 0), P['oscuro'], bev=0.08))
b.done()

# ===================================================================== CUERPO
parts = []
parts.append(cyl("Cuello", (0, 0.01, 1.72), 0.230, 0.36, m=P['piel']))
parts.append(box("Torso", (0, 0, TZ), (TW, TD, TH), m=P['traje'], bev=0.165, segs=6))
parts.append(torus("Collar", (0, 0.01, 1.812), 0.268, 0.076, m=P['claro']))
parts.append(box("Cremallera", (0, -0.370, 1.37), (0.019, 0.022, 0.330),
                 m=P['claro'], sm=False))

for s in (-1, 1):
    parts.append(capsule("Manga_%d" % s, (s*0.468, 0, 1.680), (s*0.612, -0.018, 1.245),
                         0.166, P['traje']))
    parts.append(cyl("Punho_%d" % s, (s*0.624, -0.022, 1.192), 0.190, 0.128,
                     (0, M(s*5), 0), P['metal'], bev=0.032))
    parts.append(sphere("Mano_%d" % s, (s*0.672, -0.070, 1.035), 0.186,
                        (1, 1.05, 1.08), m=P['metal']))
    parts.append(capsule("Pierna_%d" % s, (s*0.235, 0, 0.900), (s*0.245, -0.01, 0.455),
                         0.190, P['pant']))
    parts.append(box("Bota_%d" % s, (s*0.245, -0.090, 0.218), (0.240, 0.340, 0.218),
                     m=P['gris'], bev=0.10, segs=5))

group(NAME.upper(), parts + [b.empty])

# ===================================================================== SALIDA
setup_render()
studio(target=(0, 0, 1.9))
cam = camera(85)
finish_scene(NAME, OUT, cam, target=(0, 0, 1.9), ortho=4.4, dist=12.0)
