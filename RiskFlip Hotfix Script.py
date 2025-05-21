bl_info = {
    "name":        "RiskFlip v3",
    "author":      "Asterisk",
    "version":     (3, 0, 16),
    "blender":     (3, 0, 0),
    "location":    "Dope Sheet ▶ Sidebar ▶ RiskFlip",
    "description": "Onion-skin mesh ghosts, playback controls, auto-key toggle, auto-bezier, frame ranges",
    "category":    "RiskFlip v3",
}

import bpy
from bpy.props import IntProperty, BoolProperty, FloatProperty

# ─── Refresh ────────────────────────────────────────────────────────────────────

def rf_refresh(context):
    """Refresh ghosts if they are currently shown."""
    if bpy.data.collections.get("RiskFlip_Ghosts"):
        bpy.ops.rf.toggle_ghost()
        bpy.ops.rf.toggle_ghost()

# ─── Scene Properties ─────────────────────────────────────────────────────────

def register_props():
    sc = bpy.types.Scene
    sc.rf_interp_frames = BoolProperty(
        name="Interp Frame Range",
        description="Show ghosts on every frame in interp range",
        default=False,
        update=lambda s,c: rf_refresh(c)
    )
    sc.rf_key_start = IntProperty(
        name="Key Range Start",
        description="Start frame for keyed-frame ghosts",
        default=1, min=0,
        update=lambda s,c: rf_refresh(c)
    )
    sc.rf_key_end = IntProperty(
        name="Key Range End",
        description="End frame for keyed-frame ghosts",
        default=250, min=0,
        update=lambda s,c: rf_refresh(c)
    )
    sc.rf_interp_start = IntProperty(
        name="Interp Range Start",
        description="Start frame for interp-frame ghosts",
        default=1, min=0,
        update=lambda s,c: rf_refresh(c)
    )
    sc.rf_interp_end = IntProperty(
        name="Interp Range End",
        description="End frame for interp-frame ghosts",
        default=250, min=0,
        update=lambda s,c: rf_refresh(c)
    )

def unregister_props():
    sc = bpy.types.Scene
    for p in ("rf_interp_frames","rf_key_start","rf_key_end","rf_interp_start","rf_interp_end"):
        if hasattr(sc, p):
            delattr(sc, p)

# ─── Operators ─────────────────────────────────────────────────────────────────

class RF_OT_toggle_ghost(bpy.types.Operator):
    """Show or hide mesh ghosts for the selected object(s)"""
    bl_idname = "rf.toggle_ghost"
    bl_label = "Toggle Mesh Ghosts"
    bl_description = "Create or remove onion-skin mesh duplicates in the Dope Sheet range"
    def execute(self, context):
        sc = context.scene
        deps = context.evaluated_depsgraph_get()
        old = bpy.data.collections.get("RiskFlip_Ghosts")
        if old:
            for o in old.objects:
                bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.collections.remove(old)
            sc.frame_set(sc.frame_current)
            sc["rf_ghost_frames"] = []
            return {'FINISHED'}

        gc = bpy.data.collections.new("RiskFlip_Ghosts")
        context.scene.collection.children.link(gc)

        current = sc.frame_current
        frames = []
        targets = []

        for obj in context.selected_objects:
            if obj.type == 'ARMATURE':
                targets += [c for c in obj.children if c.type == 'MESH']
            elif obj.type == 'MESH':
                targets.append(obj)

        ks, ke = sc.rf_key_start, sc.rf_key_end
        if ke < ks: ks, ke = ke, ks
        is_, ie = sc.rf_interp_start, sc.rf_interp_end
        if ie < is_: is_, ie = ie, is_

        if sc.rf_interp_frames:
            frames = list(range(is_, ie + 1))
        else:
            keyset = set()
            for mesh in targets:
                arm = mesh.find_armature()
                ad = arm.animation_data if arm else mesh.animation_data
                if not(ad and ad.action): continue
                for fcu in ad.action.fcurves:
                    for kp in fcu.keyframe_points:
                        f = int(kp.co[0])
                        if ks <= f <= ke:
                            keyset.add(f)
            frames = sorted(keyset)

        sc["rf_ghost_frames"] = frames

        for frame in frames:
            sc.frame_set(frame)
            for mesh in targets:
                ev = mesh.evaluated_get(deps)
                data = bpy.data.meshes.new_from_object(ev,
                            preserve_all_data_layers=True, depsgraph=deps)
                dup = bpy.data.objects.new(f"{mesh.name}_ghost_{frame}", data)
                dup.matrix_world = mesh.matrix_world.copy()
                dup.hide_render = True
                gc.objects.link(dup)
        sc.frame_set(current)
        return {'FINISHED'}

class RF_OT_play(bpy.types.Operator):
    """Start playback"""
    bl_idname = "rf.play"
    bl_label = "Play"
    bl_description = "Play the animation in the timeline"
    def execute(self, context):
        bpy.ops.screen.animation_play()
        return {'FINISHED'}

class RF_OT_pause(bpy.types.Operator):
    """Pause playback"""
    bl_idname = "rf.pause"
    bl_label = "Pause"
    bl_description = "Pause the animation if it is playing"
    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        return {'FINISHED'}

class RF_OT_stop(bpy.types.Operator):
    """Stop playback and reset"""
    bl_idname = "rf.stop"
    bl_label = "Stop"
    bl_description = "Stop playback and return to start frame"
    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        context.scene.frame_set(context.scene.frame_start)
        return {'FINISHED'}

class RF_OT_toggle_autokey(bpy.types.Operator):
    """Toggle auto-key insertion"""
    bl_idname = "rf.toggle_autokey"
    bl_label = "Toggle Auto-Key"
    bl_description = "Enable or disable automatic keyframe insertion"
    def execute(self, context):
        ts = context.scene.tool_settings
        ts.use_keyframe_insert_auto = not ts.use_keyframe_insert_auto
        return {'FINISHED'}

class RF_OT_auto_bezier(bpy.types.Operator):
    """Auto-set handles to Bezier"""
    bl_idname = "rf.auto_bezier"
    bl_label = "Auto-Bezier"
    bl_description = "Convert all keyframe handles to auto-bezier for smooth curves"
    def execute(self, context):
        for obj in context.selected_objects:
            ad = obj.animation_data
            if not(ad and ad.action): continue
            for fcu in ad.action.fcurves:
                for kp in fcu.keyframe_points:
                    kp.handle_left_type  = 'AUTO'
                    kp.handle_right_type = 'AUTO'
        rf_refresh(context)
        return {'FINISHED'}

class RF_OT_set_speed(bpy.types.Operator):
    """Adjust scene FPS"""
    bl_idname = "rf.set_speed"
    bl_label = "Set Anim Speed"
    bl_description = "Multiply the scene's FPS by a factor"
    speed: FloatProperty(name="Speed Factor", default=1.0, min=0.1, max=10.0)
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    def execute(self, context):
        sc = context.scene
        sc.render.fps = max(1, int(sc.render.fps * self.speed))
        return {'FINISHED'}

class RF_OT_purge_static(bpy.types.Operator):
    """Simplify curves by removing every other key"""
    bl_idname = "rf.purge_static"
    bl_label = "Delete Static Keys"
    bl_description = "Remove every second keyframe to reduce density"
    def execute(self, context):
        for obj in context.selected_objects:
            ad = obj.animation_data
            if not(ad and ad.action): continue
            for fcu in ad.action.fcurves:
                pts = list(fcu.keyframe_points)
                for i, kp in enumerate(pts):
                    if i % 2 == 1:
                        try: fcu.keyframe_points.remove(kp)
                        except: pass
        rf_refresh(context)
        return {'FINISHED'}

class RF_OT_goto_frame(bpy.types.Operator):
    """Jump to a specific frame"""
    bl_idname = "rf.goto_frame"
    bl_label = "Go to Frame"
    bl_description = "Set the timeline and Dope Sheet to this frame"
    frame: IntProperty()
    def execute(self, context):
        context.scene.frame_set(self.frame)
        return {'FINISHED'}

# ─── Panel ────────────────────────────────────────────────────────────────────

class RF_PT_panel(bpy.types.Panel):
    bl_label = "RiskFlip v3"
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'UI'
    bl_category = "RiskFlip"

    def draw(self, context):
        sc = context.scene
        L = self.layout

        # frame ranges
        L.prop(sc, "rf_interp_frames")
        box = L.box()
        box.label(text="Keyed Frames Range")
        box.prop(sc, "rf_key_start")
        box.prop(sc, "rf_key_end")
        box = L.box()
        box.label(text="Interp Frames Range")
        box.prop(sc, "rf_interp_start")
        box.prop(sc, "rf_interp_end")

        # ghost toggle
        L.operator("rf.toggle_ghost")

        # playback controls
        row = L.row(align=True)
        row.operator("rf.play")
        row.operator("rf.pause")
        row.operator("rf.stop")

        # auto-key checkbox (reflects current state)
        ts = context.scene.tool_settings
        L.prop(ts, "use_keyframe_insert_auto", text="Auto-Key")

        # curve smoothing
        L.operator("rf.auto_bezier")

        # speed & cleanup
        L.operator("rf.set_speed")
        L.operator("rf.purge_static")

        # frame jump buttons
        frames = sc.get("rf_ghost_frames", [])
        if frames:
            fb = L.box()
            fb.label(text="Ghost Frames:")
            for f in frames:
                op = fb.operator("rf.goto_frame", text=str(f))
                op.frame = f

# ─── Registration ─────────────────────────────────────────────────────────────

classes = (
    RF_OT_toggle_ghost,
    RF_OT_play,
    RF_OT_pause,
    RF_OT_stop,
    RF_OT_toggle_autokey,
    RF_OT_auto_bezier,
    RF_OT_set_speed,
    RF_OT_purge_static,
    RF_OT_goto_frame,
    RF_PT_panel,
)

def register():
    register_props()
    for c in classes:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes):
        try: bpy.utils.unregister_class(c)
        except: pass
    unregister_props()

if __name__ == "__main__":
    register()
