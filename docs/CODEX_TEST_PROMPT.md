You are working in a Godot 4.7.2 + Blender 4.5 game project on Windows 10, in PowerShell.

Project folder (a git worktree): D:\blender\Blender-Fable-5.2\.claude\worktrees\house
Branch: claude/sweet-fermat-oxmviq (remote: origin)

DO NOT touch the main folder D:\blender\Blender-Fable-5.2 itself (it is on the old town-v1 branch with an
abandoned merge). DO NOT commit, push, rebase, reset --hard or delete anything. DO NOT edit
game/tools/texture_policy.py. Do not "fix" failures: if a step fails, record the exact command and output,
and carry on with the next step. Ignore scripts/*.sh (Linux only).

Set these first:
    $GODOT = "$env:LOCALAPPDATA\Godot-4.7.2\Godot_v4.7.2-stable_win64_console.exe"
    $BLENDER = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
    cd D:\blender\Blender-Fable-5.2\.claude\worktrees\house

STEP 1 - Get every change from the branch
1. Run `git status --short`.
2. Godot rewrites line endings in many .import files. For every modified file, run
   `git diff --ignore-cr-at-eol --quiet -- <file>`; if it exits 0 the change is line endings only:
   `git checkout -- <file>`.
3. If anything is still modified or untracked, list it for me, then
   `git stash push -u -m "before-pull"` and tell me exactly what was stashed.
4. `git lfs install --local`
   `git fetch origin claude/sweet-fermat-oxmviq`
   `git merge --ff-only origin/claude/sweet-fermat-oxmviq`
   `git lfs pull`
5. Print `git log --oneline -8`. HEAD must be fd740d6 or newer.
6. Check that no Git LFS pointer files are left: list every .png .jpg .glb .gltf .bin .blend .fbx under
   game\ and projects\ whose first bytes are "version https://git-lfs". There must be none; if there are,
   run `git lfs pull` again and re-check.

STEP 2 - Import (twice, with the town texture settings in between)
    & $GODOT --headless --path game --import
    python projects/03-town/godot_imports.py
    & $GODOT --headless --path game --import
Report every ERROR line. Known and harmless: "hair_diff.png" / "lashes_diff.png" missing, and
png_driver_common / image.is_null errors coming from the character FBX files.

STEP 3 - The three self-tests (each must exit 0; quote every line that starts with TEST or PRESET)
    & $GODOT --headless --path game -- --selftest
    & $GODOT --headless --path game -- --preset-check
    & $GODOT --headless --path game -- --world=town --town-selftest
Expected: --selftest ends with "TEST spring arm pulls in indoors: PASS"; --preset-check prints
"PRESET CHECK night matches main.gd: true"; the town test prints 7 lines ending in PASS and no FAIL.

STEP 4 - The town builds from source (reproducibility check; the result is NOT kept)
    & $BLENDER -b --factory-startup -P projects/03-town/build.py -- town
It must print "FENCE_CHECK 39 fence pieces, 0 hits" and a "STATS ... triangles=..." line and exit 0.
Quote both lines. Then put the committed build back:
    git checkout -- projects/03-town/town.blend game/assets/town
    git clean -n game/assets/town      (show me; only if it lists files, run git clean -f game/assets/town)
and run STEP 2 again.

STEP 5 - Frame rate on this machine (Intel HD 620). These need a window: no --headless.
    & $GODOT --path game --resolution 1280x720 -- --world=town --town-perf --quality=low
    & $GODOT --path game --resolution 1280x720 -- --world=town --town-perf --quality=high
Quote every PERF line (FPS, worst frame, draw calls, triangles, video memory).

STEP 6 - Screenshots (need a window). They are written to game\screenshots\.
    & $GODOT --path game --resolution 960x540 --script res://tools/town_views.gd -- --world=town --preset=1000_clear --lots
    & $GODOT --path game --resolution 960x540 --script res://tools/town_views.gd -- --world=town --preset=1000_clear --survey
    & $GODOT --path game --resolution 960x540 --script res://tools/town_views.gd -- --world=town --survey
    & $GODOT --path game --resolution 960x540 --script res://tools/town_views.gd -- --world=town --preset=1000_clear --only=tree_close,tree_street,tree_base,tree_edge,leaves_fall,sedan_close,wagon_close,crashed_close,west_car_close,l4_fence,l5_fence
    & $GODOT --path game --resolution 1280x720 --script res://tools/town_player_shot.gd -- --world=town --preset=1000_clear
    & $GODOT --path game --script res://tools/character_check.gd
Note: the third command is night (no preset) and overwrites the day survey images; copy
game\screenshots\town_s*.png to a folder game\screenshots\_day_survey\ between the second and third
command so I can see both. Open the images and, for each, write one line: what it shows and anything that
looks wrong (floating objects, things through walls or fences, black or stretched textures, missing
pieces, grass blobs, cards facing the wrong way). Also quote every CHECK line from character_check
(the left-hand lines must say "palm 0.0 cm").

STEP 7 - Start the game for me to play
    & $GODOT --path game -- --world=town
(and the house alone: `& $GODOT --path game`). Give me this checklist to tick off while I play:
- Mouse orbits the camera; W walks where the camera looks; W+A goes diagonally; the body turns to the
  way it walks; Shift runs; Space jumps.
- V switches first person / over the shoulder. First person: head hidden, rifle low right, dot in the
  middle; hold right mouse: view zooms, eye goes behind the red dot sight, dot centred; left mouse fires.
- Third person, right mouse: body turns to the camera, left hand closes on the rifle's fore grip.
- House: E opens doors, F flashlight, stairs work, camera pulls in near walls.
- F1 High/Low, F3 FPS counter, F2 next time of day, F4 settings, F6 free camera.
- Town: no fence runs through a house, porch or steps; lawns read as dead grass with bare earth, worn
  trails and leaves (no big identical grass blobs); small grass tufts along fences, foundations and kerbs;
  bare trees with fine twig crowns and roots; wet dark roads with a sheen at night; dry leaves falling
  slowly round the camera; textures on houses, roads and fences at a believable size.
- Note the F3 FPS at the front door, the junction and Mill Road, on Low and on High.

STEP 8 - Report and tidy up
- A table: every step, PASS / FAIL, and the key numbers (TEST lines, FENCE_CHECK, STATS, PERF).
- Every ERROR or FAIL with the exact command and output.
- The screenshot notes from STEP 6.
- Then run the line-ending rule from STEP 1.2 again, so `git status` shows only the new or changed
  screenshots, and print `git status --short`. Do not commit or push anything.
- If you stashed something in STEP 1.3, remind me it is in `git stash list`.
