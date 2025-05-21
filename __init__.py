bl_info = {
    "name":        "RiskFlip v3",
    "author":      "Asterisk",
    "version":     (3, 0, 16),
    "blender":     (3, 6, 2),
    "location":    "Dope Sheet ▶ Sidebar ▶ RiskFlip",
    "description": "Onion-skin mesh ghosts, playback controls, auto-key toggle, auto-bezier, frame ranges",
    "category":    "Animation",
}

from .core import register as core_register, unregister as core_unregister

def register():
    core_register()

def unregister():
    core_unregister()
