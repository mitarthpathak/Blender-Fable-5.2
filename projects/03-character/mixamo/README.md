# Mixamo files go here

Put the files you download from [Mixamo](https://www.mixamo.com) in this
folder with exactly these names (lower case):

| File | What to download | Mixamo settings |
| --- | --- | --- |
| `character.fbx` | The rigged character, in its T-pose | Format **FBX Binary**, Pose **T-pose**, **With Skin** |
| `idle.fbx` | A standing idle, ideally one holding a rifle | **Without Skin**, 30 fps |
| `walk.fbx` | A walk forwards | **Without Skin**, 30 fps, tick **In Place** |
| `run.fbx` | A run forwards | **Without Skin**, 30 fps, tick **In Place** |
| `rifle_aim.fbx` | Standing, rifle aimed | **Without Skin**, 30 fps |
| `fire.fbx` | One shot from the aimed pose | **Without Skin**, 30 fps |
| `jump.fbx` | A jump on the spot | **Without Skin**, 30 fps, tick **In Place** |

`character.fbx` and `idle.fbx` are required. The other five are optional: a
missing one plays the idle instead.

How to get them:

1. Sign in to Mixamo, press **Upload Character** and choose
   `projects/03-character/export/human_tpose.fbx`. Place the chin, wrist,
   elbow, knee and groin markers and let it rig.
2. With that character selected, download it once with no animation chosen:
   that is `character.fbx`.
3. Pick each animation, set the options in the table, download, and rename
   the file.

Then, from the repository root:

```bash
python3 game/tools/import_character.py
godot --headless --path game --import
python3 game/tools/import_character.py
godot --headless --path game --import
```

Start the game. The capsule is replaced by the character holding the rifle:
right mouse button aims, left fires. If the rifle sits wrongly in the hand,
adjust `RIFLE_BASIS` and `RIFLE_OFFSET` at the top of
`game/scripts/character.gd`.

Commit this folder and `game/assets/character/` afterwards (FBX files are
stored in Git LFS).
