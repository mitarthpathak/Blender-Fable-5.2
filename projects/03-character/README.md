# 03 Character: base human and carbine

The player character for Halden Ridge (see `docs/ART_BIBLE.md`): an ordinary
man in a field jacket, jeans and boots, and the rifle he carries.

![Front](renders/human_front.png)

![Rifle](renders/rifle_side.png)

## The human

Made with **MPFB2 2.0.18**, the MakeHuman add-on for Blender, and the
MakeHuman system asset pack. Nothing about the body, face or clothes is
scripted geometry: `human.py` only picks MakeHuman's settings, poses the arms
with MakeHuman's own rig and T-pose, and removes skin that clothes cover.

| | |
| --- | --- |
| Triangles | 29,856 (skin 15,656, outfit 5,996, boots 4,128, hair 3,344, eyes and lashes 732) |
| Height | 1.80 m to the top of the head in boots, 1.82 m with hair |
| Pose | T-pose: arms level to within 0.01°, palms down, fingers slightly apart |
| Mesh | One object, six materials, feet on the ground at the origin, facing -Y |
| Textures | 2K base colour, normal and roughness for skin, outfit and boots; 2K hair; 1K eyes and lashes |

MakeHuman settings: male, age 0.56, muscle 0.52, weight 0.50, average
proportions; skin `middleage_caucasian_male`; hair `short02`; clothes
`male_casualsuit05` and `shoes03`.

`export/human_tpose.fbx` has no skeleton and its textures are embedded: upload
it to [Mixamo](https://www.mixamo.com) as it is and place the markers. The
`.glb` is the same mesh for looking at in Godot or a browser.

## The carbine

The first-pass rifle's design (flat-top upper, slotted handguard, skeleton
stock, angled magazine, compact optic, fore grip), modelled again at the size
of a real 5.56 carbine. It is an original design and copies no real firearm.

| | |
| --- | --- |
| Triangles | 5,972 in all |
| Size | 0.886 m long, 0.356 m tall, 51 mm wide; 0.35 m length of pull |
| Objects | `rifle` and four moving parts parented to it (below); one material |
| Axes | Muzzle along -Y in Blender (+Z in Godot); origin at the top of the pistol grip |
| Textures | 2K base colour, normal, roughness, metallic and emissive (the reticle) |

The moving parts are separate objects so they can be animated. Each has its
origin where it moves from, and carries its travel as custom properties
(glTF extras in Godot):

| Object | Pivot | Motion |
| --- | --- | --- |
| `rifle_magazine` | top of the magazine, in the well | slides down and out, about 0.20 m |
| `rifle_bolt` | middle of the bolt carrier | slides back (+Y) 0.085 m |
| `rifle_charging_handle` | its front edge | slides back (+Y) 0.075 m |
| `rifle_trigger` | its pin | turns about X, 12 degrees |

The pistol grip and fore grip are lofted through oval sections, with a palm
swell and a flared base. The optic has a lit reticle (a dot and four ticks)
on the shooter's side of its rear lens.

![Parts](renders/rifle_parts.png)

Edges are chamfered in the mesh and rounded in the normal map. The wear is
baked, not painted: Cycles records where the convex edges, the recesses and
each material are, and `compose()` in `rifle.py` turns that into anodised
aluminium worn to bare metal on its edges, phosphated steel with rust blooms,
moulded polymer polished where it is handled, and dust in the recesses.

## Files

| File | What it is |
| --- | --- |
| `fetch.py` | Downloads MPFB2 and the asset pack (checksummed) into `assets/cache/mpfb/` and installs the add-on |
| `textures.py` | Makes the human's texture sets from the MakeHuman maps |
| `human.py` | Builds, exports and renders the human |
| `rifle.py` | Builds, bakes, exports and renders the carbine |
| `export/` | `human_tpose.fbx`, `rifle.fbx`, and a `.glb` of each |
| `mixamo/` | Where the rigged character and its animations go: see `mixamo/README.md` |
| `textures/` | The texture sets, as files |
| `renders/` | `human_{front,side,back}.png`, `rifle_{side,detail,parts}.png` |

```bash
python3 projects/03-character/fetch.py
python3 projects/03-character/textures.py
blender -b --python projects/03-character/human.py
blender -b --python projects/03-character/rifle.py
```

## Licences

- MPFB2 is GPL-3.0-or-later. It is a tool here: its code is not in this
  repository.
- The MakeHuman assets used (base mesh, targets, skin, hair, clothes) are CC0.
  Characters exported from MakeHuman are CC0 as well.

## Known shortfalls

- The face is MakeHuman's average face. It is realistic in proportion but
  generic, and its skin has only a colour photo behind it: the normal and
  roughness maps are derived from that photo, so there are no sculpted pores
  or wrinkles.
- Hair is a low-polygon cap with a painted texture, not hair cards.
- The jacket and jeans are MakeHuman's stock outfit at 6,000 triangles. The
  folds are in the normal map only, and the jacket is cut loose.
- 29,856 triangles is at the top of the 20-30k budget. Over half is the head
  and hands, which MakeHuman models densely (inner mouth included).
- The teeth and tongue were left out to stay in budget, so the mouth cannot
  open onto anything yet.
- The rifle is solid: with the magazine out there is no magazine well to
  look into, and the bolt slides over a flat pocket. The reticle is painted
  on the rear lens, not projected, so it does not stay on target as the eye
  moves.
- Not yet rigged: Mixamo needs a browser and an Adobe login, which a cloud
  session does not have. The Godot side is ready for the files
  (`mixamo/README.md`, `game/scripts/character.gd`); it was tested with a
  stand-in rig, so the rifle's position in the hand is a first guess.
