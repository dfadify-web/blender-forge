---
name: blender
description: "Modelado procedural rapido en Blender: personajes (chibi, props, hard-surface), mapas y mundos (terreno, tilemaps ASCII, scatter, edificios), con render de fichas de 4 vistas y export a .glb. Usar siempre que se pida crear/modificar un modelo 3D, un personaje, un nivel, un escenario o un asset para Blender, Unity, Godot, three.js o web. Trigger: /blender"
---

# /blender — modelado procedural rapido

Modelar a mano en Blender es lento y no se puede iterar. Aqui **el script ES el modelo**:
se escribe un `.py`, se ejecuta Blender headless, se MIRA el render y se ajustan numeros.
La libreria `bforge` trae ya resueltas las partes que siempre cuestan (detalles pegados a
superficies curvas, cascaras, aperturas, terreno, mapas, iluminacion, fichas de vistas).

## Uso

```
/blender <que modelar>                 # personaje, prop, mapa, mundo...
/blender personaje <descripcion|imagen de referencia>
/blender mapa|mundo <descripcion>
/blender editar <ruta_script.py> <cambios>
```

## Flujo de trabajo (NO te lo saltes)

1. **Medir la referencia.** Si hay imagen, saca proporciones en fracciones de la altura
   total y del ancho de la cabeza (ej: "cabeza = 49% del total", "ojo = 27% del ancho de
   cabeza"). Escribe esos numeros como constantes arriba del script.
2. **Escribir un solo script** `build_<nombre>.py` que importe `bforge` (plantillas abajo).
3. **Ejecutar en modo iteracion** (rapido, 1-2 vistas):
   ```
   BF_SAMPLES=48 BF_VIEWS=front,34 BF_GLB=0 "<BLENDER>" -b --factory-startup --python build_x.py
   ```
4. **MIRAR el PNG con la tool Read.** Nunca des por bueno un modelo sin verlo. Comparalo
   con la referencia parte por parte (silueta → volumenes → detalles → color).
5. Ajustar constantes y repetir 3-4. Cada pasada corrige 3-5 cosas, no una.
6. **Pasada final:** `BF_SAMPLES=128 BF_VIEWS=front,34,side,back` + `.glb`.

Ejecutar en background (`run_in_background: true`) si el render pasa de ~2 min, y avisar
que se esta renderizando en vez de bloquear.

## Comando

Blender (Windows, ajusta la version si cambia):
```
"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe" -b --factory-startup --python build_x.py
```
`--factory-startup` evita addons del usuario y hace el arranque mucho mas rapido.

Variables de entorno: `BF_SAMPLES`, `BF_VIEWS` (front,34,side,back,orbit,none),
`BF_RES` (900x1000), `BF_ENGINE` (CYCLES|EEVEE), `BF_GLB`, `BF_BLEND`.

## Esqueleto minimo

```python
import sys, os
for _p in (os.environ.get("BFORGE_LIB"),
           os.path.expanduser("~/.claude/skills/blender/lib"),
           os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")):
    if _p and os.path.isdir(_p):
        sys.path.insert(0, _p); break
from bforge import *

OUT = os.path.join(os.path.expanduser("~"), "Desktop", "mi_proyecto")

clear()
P = palette(piel="#A32BD4", traje="#451676", metal=("#C6C8D6", dict(rough=.34, metal=.2)))

# ... construir ...

setup_render()
studio(target=(0, 0, 1.9))
cam = camera()
finish_scene("mi_modelo", OUT, cam, target=(0, 0, 1.9), ortho=4.4, dist=12)
```

## Los 8 errores que se cometen SIEMPRE (leelos antes de escribir)

1. **`v.co` es LOCAL.** Deformar vertices comparando con una Z de mundo destroza la malla.
   Si el objeto se creo en `location=(0,0,2.9)`, sus vertices van de -r a +r.
2. **Un detalle facial NO es una esfera aplastada delante de la cara.** Se hunde por arriba
   y flota por el centro. Usa `Ball.patch()` = esfera ∩ cilindro orientado al centro.
3. **El sello de un patch debe ir solo hacia delante**, si no aparece el mismo detalle
   duplicado en la nuca (ya resuelto dentro de `patch()`; si lo haces a mano, recuerdalo).
4. **Un hueco en un casco/cupula se corta con un CONO desde el centro** (`cone_cutter`),
   no con un cilindro: el cilindro corta en plano y deja el lateral pelado.
5. **Una banda sobre una esfera debe ser una cascara** (`shell` = out − in). Una esfera
   solida cortada por un plano parece la visera de una gorra, no unas gafas.
6. **Barras finas de detalle: `sm=False`.** Con auto-smooth se ven negras/sucias.
7. **Una cascara debe ser fina** (0.03–0.05 del radio). Gruesa parece un tunel y hunde la cara.
8. **No confies en la geometria "sobre el papel": renderiza y mira.** La mitad de los fallos
   (partes ocultas dentro de otras, detalles a contraluz, escalas) solo se ven en el render.

Extra: booleanas siempre con solver `EXACT`; el objeto debe estar activo y seleccionado
(`act(o)` lo hace); aplica rotacion/escala antes de bolear (`apply_tr`).

## Cheat sheet de `bforge`

**Color** `srgb(hex)` · `mat(nombre, hex, rough, metal, emis, estr, alpha)` · `palette(**kw)`

**Escena** `clear()` · `act(o)` · `smooth(o, ang)` · `flat(o)` · `apply_tr(o)` · `group(nombre, objs)`

**Primitivas** `sphere box cyl cone torus plane capsule star poly_prism text3d`
(en `box`, `sc` = SEMI-ejes; `bev=` bisela)

**Modificadores** `bevel subsurf solidify decimate array mirror_x add_mod`

**Booleanas** `cut(a,b)` `inter(a,b)` `union(a,b)` `join([objs], nombre)`

**Superficies curvas — clase `Ball`** (cabezas, cascos, planetas, cupulas):
```python
b = Ball(center=(0,0,2.70), r=0.95, squash=(1,0.94,1))
b.skin("Cabeza", P['piel'], taper=0.11)             # esfera base + menton
b.patch("Ojo_L", -0.28, -0.19, 0.28, 0.25, P['negro'], k=1.045, roll=M(9))
casco = b.shell("Casco", 1.055, 1.018, P['casco'])  # cascara fina
cut(casco, b.cone_cutter(dz=-0.32, hax=45, haz=52)) # abrir la cara
b.band("Gafas", 1.108, 1.040, P['cian'],            # banda curva
       b.ellip_cyl(cz=0.51, hx=1.8, hz=0.25), front=-0.15)
b.done()                                            # aplica el squash a todo
```
`patch(name, px, pz, hx, hz, m, k, roll)`: px/pz = punto sobre la esfera, hx/hz = semiejes
del detalle, k = cuanto sobresale (1.045 ≈ pegado), roll = giro sobre la normal.

**Mundos** `terrain(size,res,height,scale,seed,island,ridged)` · `sample_terrain(t,x,y)` ·
`water()` · `tilemap(rows, builders, tile)` · `scatter(builder,n,area,seed,zfn)` · `radial()`

**Assets** `tree rock crystal platform building road fence`

**Render** `setup_render()` · `studio(target)` para fichas · `outdoor(sun,sky)` para mapas ·
`camera()` · `shot(cam,path,loc,target,ortho)` · `sheet()` 4 vistas · `orbit()`

**Salida** `finish_scene(base, out_dir, cam, target, ortho, dist)` guarda .blend + renders + .glb ·
`append_blend(path)` reutiliza personajes ya hechos dentro de un mapa.

**Rig** `quick_rig(objs)` — armature basica + auto weights para posar o exportar a motor.

## Plantillas

- `templates/character.py` — chibi completo (cabeza Ball + cara + casco + cuerpo + ficha 4 vistas).
- `templates/world.py` — terreno + tilemap ASCII + scatter de props + camara aerea.

Copia la plantilla al directorio del proyecto, renombra y edita constantes. No empieces de cero.

## Reglas de entrega

- Guardar siempre en el directorio del proyecto del usuario, no en temp.
- Dejar el `.py` junto al `.blend`: **el script es la fuente de verdad**, el .blend es un output.
- Entregar `.glb` si el destino es un juego o web.
- En el mensaje final: que se ha creado, donde, y el comando exacto para re-generar.
