class_name HouseLights
## The lights that arrive with the house model, configured in one place so
## the running game and the editor (for baking lightmaps) see the same thing.

const WARM := Color(1.0, 0.62, 0.34)
const MOONLIGHT := Color(0.50, 0.66, 1.0)
const SODIUM := Color(1.0, 0.55, 0.20)
const TUBE := Color(0.74, 0.90, 0.86)           # the kitchen's failing fluorescent strip
const LOW_FOG_INDOORS := Color(0.112, 0.144, 0.192)
const LOW_FOG_OUTDOOR_GAIN := 1.75             # outdoors the fog is this much paler than indoors


## Configure every light under `root`. Returns {"moon": light, "lamps": [...]}.
static func apply(root: Node) -> Dictionary:
	var result := {"moon": null, "lamps": []}
	var stack: Array[Node] = [root]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		for child in node.get_children():
			stack.append(child)
		if node is MeshInstance3D:
			var mesh := node as MeshInstance3D
			var mesh_name := String(mesh.name)
			# What the lightmap bake should leave alone. Doors move, so they take
			# their light from the probes; decals, glass and haze get no lightmap.
			if (mesh_name.begins_with("door_") or mesh_name.ends_with("_door")) and not mesh_name.begins_with("frame_"):
				mesh.gi_mode = GeometryInstance3D.GI_MODE_DYNAMIC
			elif mesh_name.begins_with("decals_") or mesh_name.begins_with("glass_") \
					or mesh_name.begins_with("shade_") or mesh_name.begins_with("fog_"):
				mesh.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
			if mesh_name.begins_with("clapboard_"):
				# The boards' own shadow lines are finer than a shadow map can hold:
				# left on, they speckle the wall. Their undersides stay dark anyway.
				mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			elif mesh_name == "roof":
				mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_DOUBLE_SIDED
		elif node is DirectionalLight3D:
			var moon := node as DirectionalLight3D
			moon.light_color = MOONLIGHT
			moon.light_energy = 1.6
			moon.light_angular_distance = 0.6
			moon.shadow_enabled = true
			moon.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
			moon.directional_shadow_max_distance = 26.0
			moon.shadow_bias = 0.04
			moon.shadow_normal_bias = 1.2
			moon.shadow_blur = 1.5
			moon.light_volumetric_fog_energy = 2.2
			moon.light_bake_mode = Light3D.BAKE_DYNAMIC      # direct light live, bounce baked
			result["moon"] = moon
		elif node is OmniLight3D:
			var lamp := node as OmniLight3D
			var n := String(lamp.name)
			lamp.light_color = WARM
			lamp.omni_range = 3.8
			lamp.omni_attenuation = 1.6
			lamp.shadow_enabled = true
			lamp.shadow_bias = 0.06
			lamp.shadow_blur = 1.6
			lamp.light_size = 0.04
			lamp.light_volumetric_fog_energy = 0.6
			lamp.light_energy = 0.6
			lamp.light_bake_mode = Light3D.BAKE_DYNAMIC
			if n.contains("sodium"):
				# The streetlight: dull orange, wide, and the main thing lighting the fog outside.
				lamp.light_color = SODIUM
				lamp.light_energy = 3.0
				lamp.omni_range = 26.0
				lamp.omni_attenuation = 1.2
				lamp.light_volumetric_fog_energy = 3.0
			elif n.contains("porch"):
				lamp.light_energy = 0.8
				lamp.omni_range = 5.0
			if n.contains("flicker"):
				lamp.light_energy = 0.5
				lamp.light_bake_mode = Light3D.BAKE_DISABLED   # it changes, so it cannot be baked
			if n.contains("kitchen"):
				# Cool and dim, so the kitchen sits with the moonlit rooms and not above them.
				lamp.light_color = TUBE
				lamp.light_energy = 0.42
				lamp.omni_range = 4.6
			elif n.contains("hood") or n.contains("fridge"):
				lamp.light_energy = 0.32
				lamp.omni_range = 2.6
			result["lamps"].append(lamp)
	return result


## Fog for the Low quality preset, blended by how far outdoors the camera is
## (0 to 1). Indoors it is the lighting preset's own distance fog, thin enough
## for rooms to keep their contrast. Outdoors the same fog is paler and
## thicker, hides the street beyond about 25 m and pools on the ground.
static func apply_low_fog(env: Environment, outside: float, indoor_color := LOW_FOG_INDOORS,
		indoor_density := 0.055) -> void:
	var outdoor_color := indoor_color * LOW_FOG_OUTDOOR_GAIN
	outdoor_color.a = 1.0
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_light_color = indoor_color.lerp(outdoor_color, outside)
	env.fog_density = lerpf(indoor_density, indoor_density * 1.64, outside)
	env.fog_sky_affect = 1.0
	env.fog_sun_scatter = 0.0
	env.fog_aerial_perspective = 0.0
	env.fog_height = -0.45 + 1.6                 # ground fog: thickest in the first metre and a half
	env.fog_height_density = lerpf(0.0, 0.35, outside)
