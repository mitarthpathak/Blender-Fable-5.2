# 02 Soldier

An original third-person-shooter soldier and rifle, built by script.

![Front](renders/soldier_front.png)

**Status: first pass, blockout quality.** The proportions, silhouette and
surface detail are not yet at the level of the house. See "Known problems".

| File | What it is |
| --- | --- |
| `build.py` | Builds, bakes, exports and renders everything |
| `export/soldier_tpose.fbx` | The character in a T-pose, textures embedded, for Mixamo |
| `export/rifle.fbx` | The rifle, a separate object |
| `textures/` | 2K base colour, roughness and normal for each |
| `renders/` | Front, side and back previews, and the rifle |

- Soldier: 26,000 triangles, 1.80 m tall, feet on the ground at the origin,
  arms straight out, fingers apart, one mesh, one material.
- Rifle: 836 triangles, 1.07 m long.
- No face: balaclava, goggles and helmet.

```bash
blender -b --python projects/02-soldier/build.py
```

## Known problems

- The body is too slim, especially front to back, and the limbs are tubes
  with no muscle or cloth shape.
- Gear is boxes: no straps, stitching, webbing or folds.
- The head and helmet read as small; the boots are blobs on flat soles.
- Colours bake pale; the camouflage is a simple noise pattern.
- The rifle is a low-detail block model.
- The FBX has not been uploaded to Mixamo, so auto-rigging is untested.
