bl_info = {
    "name": "Ease Grid Popup",
    "author": "LuminaGlyphProd",
    "version": (1, 2, 1),
    "blender": (4, 2, 0),
    "location": "Graph Editor / Dope Sheet / Timeline > T",
    "description": "One popup for interpolation + easing (Ease In / Out / In & Out), Mine-imator style. Has an auto-updater.",
    "category": "Animation",
}

import os
import re
import sys
import threading
import time
import urllib.request

import bpy

ADDON_NAME = "Ease Grid Popup"

# ---------------------------------------------------------------------------
# UPDATER SETTINGS
# Put the raw link to the latest copy of this .py file here, for example:
#   https://raw.githubusercontent.com/<user>/<repo>/main/ease_grid_popup.py
# Whenever you upload a new version there with a higher bl_info "version",
# everyone who has this add-on gets an "Update Ease Grid Popup" button.
# ---------------------------------------------------------------------------
UPDATE_URL = "http://localhost:8000/ease_grid_popup.py"

MODULE_NAME = __name__

# ---------------------------------------------------------------------------
# Layout data
# ---------------------------------------------------------------------------

OTHER = [
    ("LINEAR", "Linear"),
    ("CONSTANT", "Constant"),
    ("BEZIER", "Bezier"),
]

# Shown as a 5-column grid (2 rows of 5), same order as Mine-imator
CURVES = [
    ("SINE", "Sine"),
    ("QUAD", "Quad"),
    ("CUBIC", "Cubic"),
    ("QUART", "Quart"),
    ("QUINT", "Quint"),
    ("EXPO", "Expo"),
    ("CIRC", "Circ"),
    ("BACK", "Back"),
    ("BOUNCE", "Bounce"),
    ("ELASTIC", "Elastic"),
]

# (easing mode, section title, icon)
EASES = [
    ("EASE_IN", "Ease In", "IPO_EASE_IN"),
    ("EASE_OUT", "Ease Out", "IPO_EASE_OUT"),
    ("EASE_IN_OUT", "Ease In & Out", "IPO_EASE_IN_OUT"),
]

INTERP_ITEMS = [(i, i.title(), "") for i, _ in OTHER + CURVES]
EASE_ITEMS = [("NONE", "None", "")] + [(e, t, "") for e, t, _ in EASES]


def _valid_icons():
    """Icon names this Blender version accepts, so a missing icon never breaks the popup."""
    try:
        params = bpy.types.UILayout.bl_rna.functions["operator"].parameters
        return set(params["icon"].enum_items.keys())
    except Exception:
        return set()


def _icon(valid, name):
    return name if name in valid else "NONE"


# ---------------------------------------------------------------------------
# Updater
# ---------------------------------------------------------------------------

_state = {
    "checking": False,   # a background check is running
    "checked": False,    # at least one check has finished
    "latest": None,      # newest version found online, as a tuple like (1, 3, 0)
    "error": "",         # last error message, if any
}

_VERSION_RE = re.compile(r'"version"\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')
# https links, plus http://localhost for hosting updates on your own computer
_URL_OK = re.compile(r"^(https://|http://(localhost|127\.0\.0\.1)(:\d+)?(/|$))", re.I)
_NAME_RE = re.compile(r'"name"\s*:\s*"' + re.escape(ADDON_NAME) + r'"')


def current_version():
    return tuple(bl_info["version"])


def version_str(v):
    return ".".join(str(x) for x in v)


def update_available():
    return _state["latest"] is not None and _state["latest"] > current_version()


def online_allowed():
    # Blender 4.2+ has a global "Allow Online Access" switch in Preferences > System > Network
    return getattr(bpy.app, "online_access", True)


def fetch_text(url):
    if not _URL_OK.match(url):
        raise ValueError("The update link must start with https:// (http://localhost is allowed for local hosting).")
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(
        url + sep + "t=" + str(int(time.time())),  # dodge cached copies
        headers={"User-Agent": "EaseGridPopup-Updater"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read(1_000_000).decode("utf-8")


def validate(text):
    """Check a downloaded file is really this add-on. Returns (version, error)."""
    if not _NAME_RE.search(text):
        return None, "The downloaded file is not this add-on."
    m = _VERSION_RE.search(text)
    if not m:
        return None, "The downloaded file has no version number."
    try:
        compile(text, "ease_grid_popup_update", "exec")
    except SyntaxError as e:
        return None, "The downloaded update has a syntax error: %s" % e
    return tuple(int(x) for x in m.groups()), ""


def _redraw_all():
    wm = bpy.context.window_manager
    for win in wm.windows:
        for area in win.screen.areas:
            area.tag_redraw()


def _poll_redraw():
    _redraw_all()
    return 0.5 if _state["checking"] else None


def _check_worker():
    try:
        text = fetch_text(UPDATE_URL)
        version, err = validate(text)
        if err:
            _state["error"] = err
        else:
            _state["latest"] = version
    except Exception as e:
        _state["error"] = str(e)
    finally:
        _state["checking"] = False
        _state["checked"] = True


def start_check():
    """Look for a new version in a background thread (never freezes Blender)."""
    if _state["checking"]:
        return
    _state["error"] = ""
    if not UPDATE_URL:
        _state["error"] = "No update link has been set in the add-on yet."
        _state["checked"] = True
        return
    if not online_allowed():
        _state["error"] = "Online access is off. Turn on Preferences > System > Network > Allow Online Access."
        _state["checked"] = True
        return
    _state["checking"] = True
    threading.Thread(target=_check_worker, daemon=True).start()
    bpy.app.timers.register(_poll_redraw, first_interval=0.5)


def _auto_check():
    try:
        prefs = bpy.context.preferences.addons[MODULE_NAME].preferences
        enabled = prefs.auto_check
    except Exception:
        enabled = True
    if enabled and UPDATE_URL:
        start_check()
    return None


def _reload_self():
    """Reload the add-on from disk so the new version runs without restarting Blender."""
    try:
        bpy.ops.preferences.addon_disable(module=MODULE_NAME)
        sys.modules.pop(MODULE_NAME, None)
        bpy.ops.preferences.addon_enable(module=MODULE_NAME)
    except Exception as e:
        print("[%s] reload failed, restart Blender to finish updating: %s" % (ADDON_NAME, e))
    return None


def install_text(text):
    """Write a validated update over this add-on's own file and schedule a reload."""
    path = globals().get("__file__")
    if not path or not os.path.isfile(path):
        raise RuntimeError("Install the add-on first (Preferences > Add-ons > Install from Disk).")
    tmp = path + ".update"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)
    bpy.app.timers.register(_reload_self, first_interval=0.3)


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class ANIM_OT_set_interp_ease(bpy.types.Operator):
    """Set keyframe interpolation and easing in one go"""
    bl_idname = "anim.set_interp_ease"
    bl_label = "Set Interpolation & Easing"
    bl_options = {'REGISTER', 'UNDO'}

    interp: bpy.props.EnumProperty(name="Interpolation", items=INTERP_ITEMS, default="BEZIER")
    ease: bpy.props.EnumProperty(name="Easing", items=EASE_ITEMS, default="NONE")

    @classmethod
    def poll(cls, context):
        sd = context.space_data
        return sd is not None and sd.type in {'GRAPH_EDITOR', 'DOPESHEET_EDITOR'}

    def execute(self, context):
        ops = bpy.ops.graph if context.space_data.type == 'GRAPH_EDITOR' else bpy.ops.action

        result = ops.interpolation_type(type=self.interp)
        if 'FINISHED' not in result:
            return {'CANCELLED'}

        if self.ease != "NONE":
            ops.easing_type(type=self.ease)

        return {'FINISHED'}


class ANIM_OT_ease_grid_check_update(bpy.types.Operator):
    """Check online for a newer version of Ease Grid Popup"""
    bl_idname = "anim.ease_grid_check_update"
    bl_label = "Check for Updates"

    def execute(self, context):
        start_check()
        if _state["error"]:
            self.report({'WARNING'}, _state["error"])
            return {'CANCELLED'}
        self.report({'INFO'}, "Checking for updates...")
        return {'FINISHED'}


class ANIM_OT_ease_grid_update(bpy.types.Operator):
    """Download and install the newest version of Ease Grid Popup"""
    bl_idname = "anim.ease_grid_update"
    bl_label = "Update " + ADDON_NAME

    def execute(self, context):
        try:
            text = fetch_text(UPDATE_URL)
        except Exception as e:
            self.report({'ERROR'}, "Could not download the update: %s" % e)
            return {'CANCELLED'}

        version, err = validate(text)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}

        _state["latest"] = version
        if version <= current_version():
            self.report({'INFO'}, "%s is already up to date (v%s)." % (ADDON_NAME, version_str(current_version())))
            return {'CANCELLED'}

        try:
            install_text(text)
        except Exception as e:
            self.report({'ERROR'}, "Could not install the update: %s" % e)
            return {'CANCELLED'}

        self.report({'INFO'}, "%s updated to v%s." % (ADDON_NAME, version_str(version)))
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# The popup (a panel, not a menu, so buttons lay out as a proper grid)
# ---------------------------------------------------------------------------

def _draw_update_button(layout):
    row = layout.row()
    row.alert = True
    row.scale_y = 1.3
    row.operator(
        ANIM_OT_ease_grid_update.bl_idname,
        text="Update %s (v%s)" % (ADDON_NAME, version_str(_state["latest"])),
        icon='IMPORT',
    )


class ANIM_PT_ease_grid(bpy.types.Panel):
    bl_idname = "ANIM_PT_ease_grid"
    bl_label = "Interpolation & Easing"
    bl_space_type = 'TOPBAR'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 17

    def draw(self, context):
        layout = self.layout
        valid = _valid_icons()
        op_id = ANIM_OT_set_interp_ease.bl_idname

        def add_button(parent, ident, label, ease):
            op = parent.operator(op_id, text=label, icon=_icon(valid, "IPO_" + ident))
            op.interp = ident
            op.ease = ease

        # Shows only when a newer version is online
        if update_available():
            _draw_update_button(layout)
            layout.separator()

        # Other: Linear / Constant / Bezier
        layout.label(text="Other")
        row = layout.row(align=True)
        for ident, label in OTHER:
            add_button(row, ident, label, "NONE")

        # Ease In / Ease Out / Ease In & Out
        for ease, title, ease_icon in EASES:
            layout.separator()
            layout.label(text=title, icon=_icon(valid, ease_icon))
            grid = layout.grid_flow(row_major=True, columns=5, even_columns=True, even_rows=True, align=True)
            for ident, label in CURVES:
                add_button(grid, ident, label, ease)


# ---------------------------------------------------------------------------
# Add-on preferences (updater controls)
# ---------------------------------------------------------------------------

class EaseGridPreferences(bpy.types.AddonPreferences):
    bl_idname = MODULE_NAME

    auto_check: bpy.props.BoolProperty(
        name="Check for updates on startup",
        description="Look online for a newer version a few seconds after Blender starts",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="%s  v%s" % (ADDON_NAME, version_str(current_version())))
        layout.prop(self, "auto_check")

        row = layout.row()
        row.enabled = not _state["checking"]
        row.operator(ANIM_OT_ease_grid_check_update.bl_idname, icon='FILE_REFRESH')

        if _state["checking"]:
            layout.label(text="Checking...", icon='TIME')
        elif update_available():
            _draw_update_button(layout)
        elif _state["error"]:
            layout.label(text=_state["error"], icon='ERROR')
        elif _state["checked"]:
            layout.label(text="You're on the latest version.", icon='CHECKMARK')


# ---------------------------------------------------------------------------
# Registration + hotkey (T in Graph Editor, Dope Sheet, Timeline)
# ---------------------------------------------------------------------------

classes = (
    ANIM_OT_set_interp_ease,
    ANIM_OT_ease_grid_check_update,
    ANIM_OT_ease_grid_update,
    ANIM_PT_ease_grid,
    EaseGridPreferences,
)
addon_keymaps = []


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is not None:  # None in background mode
        for km_name, space in (("Graph Editor", "GRAPH_EDITOR"), ("Dopesheet", "DOPESHEET_EDITOR")):
            km = kc.keymaps.new(name=km_name, space_type=space)
            kmi = km.keymap_items.new("wm.call_panel", 'T', 'PRESS')
            kmi.properties.name = ANIM_PT_ease_grid.bl_idname
            addon_keymaps.append((km, kmi))

    if not bpy.app.background:
        bpy.app.timers.register(_auto_check, first_interval=5.0)


def unregister():
    for fn in (_auto_check, _poll_redraw):
        if bpy.app.timers.is_registered(fn):
            bpy.app.timers.unregister(fn)

    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    addon_keymaps.clear()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
