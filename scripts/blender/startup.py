"""Session defaults for the Blender started by scripts/blender-up.sh.

Passed to Blender with --python, so it runs once at launch; the load_post
handler re-applies it whenever another .blend is opened.
"""

import bpy
from bpy.app.handlers import persistent


@persistent
def apply_session_defaults(_unused=None):
    for scene in bpy.data.scenes:
        # Poly Haven (CC0 HDRIs, textures and models) needs no account or key,
        # so the addon's asset search works out of the box. The other
        # libraries and the 3D generators stay off until someone adds a key.
        if hasattr(scene, "blendermcp_use_polyhaven"):
            scene.blendermcp_use_polyhaven = True


if apply_session_defaults not in bpy.app.handlers.load_post:
    bpy.app.handlers.load_post.append(apply_session_defaults)
apply_session_defaults()
