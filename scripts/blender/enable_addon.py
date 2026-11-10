"""Enable the MCP for Blender addon and save preferences.

Run by scripts/install-blender.sh as:  blender --background --python enable_addon.py
Exits non-zero if the addon could not be enabled, so the installer fails loudly.
"""

import sys

import addon_utils
import bpy

ADDON_NAMES = {"MCP for Blender", "Blender MCP"}


def find_module():
    for mod in addon_utils.modules(refresh=True):
        if addon_utils.module_bl_info(mod).get("name") in ADDON_NAMES:
            return mod.__name__
    return None


def main():
    module = find_module()
    if module is None:
        print("enable_addon: addon file not found in Blender's addon paths")
        return 1

    prefs = bpy.context.preferences
    if module not in {a.module for a in prefs.addons}:
        if addon_utils.enable(module, default_set=True) is None:
            print(f"enable_addon: Blender could not load {module}")
            return 1

    # Collection of prompts, code and screenshots is opt-in upstream. Pin it
    # off explicitly so a changed default can never switch it on here.
    addon_prefs = prefs.addons[module].preferences
    if hasattr(addon_prefs, "telemetry_consent"):
        addon_prefs.telemetry_consent = False

    # Nobody is sitting in front of this Blender to dismiss a splash screen.
    prefs.view.show_splash = False

    bpy.ops.wm.save_userpref()
    print(f"enable_addon: {module} enabled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
