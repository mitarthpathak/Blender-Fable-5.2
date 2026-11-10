class_name HouseLights
## The lights that arrive with the house model, configured in one place so
## the running game and the editor (for baking lightmaps) see the same thing.

const WARM := Color(1.0, 0.62, 0.34)
const MOONLIGHT := Color(0.50, 0.66, 1.0)
const SODIUM := Color(1.0, 0.55, 0.20)


## Configure every light under `root`. Returns {"moon": light, "lamps": [...]}.
static func apply(root: Node) -> Dictionary:
	var result := {"moon": null, "lamps": []}
	var stack: Array[Node] = [root]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		for child in node.get_children():
			stack.append(child)
		if node is DirectionalLight3D:
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
			result["lamps"].append(lamp)
	return result
