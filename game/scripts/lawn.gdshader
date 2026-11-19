// The town's lawns: dead autumn grass, bare trodden earth and dry leaf litter,
// blended by a mask instead of one texture tiled flat.
//
// - Grass (withered_grass) is sampled twice, at two sizes and angles, mixed by
//   a slow noise, so its repeat does not show.
// - Earth (park_dirt) comes through where the mesh's vertex alpha says
//   (street_kit.lawn_grid: bare patches, the drip line round each house, worn
//   path edges and trails), its edge broken up by a finer noise.
// - Leaves (dry_decay_leaves) lie in drifts from a slow noise; leaf_amount
//   says how much of the lawn they cover.
// - The vertex colour's RGB is the lawn tint Blender's material multiplied in.
// All mapped in world space (x, z), so the lots join without seams.
shader_type spatial;

uniform sampler2D grass_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass_arm : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform sampler2D rough_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;   // darker, coarser grass
uniform sampler2D dirt_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D dirt_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D dirt_arm : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform sampler2D leaf_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D leaf_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D leaf_arm : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform sampler2D noise_tex : filter_linear_mipmap, repeat_enable;
uniform float grass_size = 2.5;
uniform float dirt_size = 2.0;
uniform float leaf_size = 1.8;
uniform float leaf_amount : hint_range(0.0, 1.0) = 0.35;
uniform float tint_gain = 0.8;
uniform float rough_size = 1.8;

varying vec3 world;
varying vec4 vcol;

vec2 turn(vec2 p, float a) {
	float c = cos(a), s = sin(a);
	return vec2(c * p.x - s * p.y, s * p.x + c * p.y);
}

void vertex() {
	world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vcol = COLOR;
}

void fragment() {
	vec2 p = world.xz;
	float slow = texture(noise_tex, p * 0.035).r;
	float fine = texture(noise_tex, p * 0.23 + vec2(0.37, 0.61)).r;

	vec2 g1 = p / grass_size;
	vec2 g2 = turn(p, 0.83) / (grass_size * 1.7);
	float swap = smoothstep(0.38, 0.62, slow);
	vec3 g_alb = mix(texture(grass_albedo, g1).rgb, texture(grass_albedo, g2).rgb, swap);
	vec3 g_nor = mix(texture(grass_normal, g1).rgb, texture(grass_normal, g2).rgb, swap);
	vec3 g_arm = mix(texture(grass_arm, g1).rgb, texture(grass_arm, g2).rgb, swap);
	// a darker, coarser grass through about half of it, so no lawn is one tone
	float coarse = smoothstep(0.42, 0.58, texture(noise_tex, p * 0.05 + vec2(0.13, 0.71)).r);
	g_alb = mix(g_alb, texture(rough_albedo, turn(p, 2.6) / rough_size).rgb, coarse * 0.6);
	g_alb *= vcol.rgb * tint_gain;

	vec2 d = turn(p, 0.4) / dirt_size;
	vec2 l = turn(p, 1.9) / leaf_size;
	float dirt = clamp((vcol.a - 0.45 + (fine - 0.5) * 0.6) * 3.0, 0.0, 1.0);
	float leaves = clamp((slow * 0.65 + fine * 0.35 - (1.0 - leaf_amount)) * 4.0, 0.0, 1.0) * (1.0 - 0.6 * dirt);

	vec3 alb = mix(g_alb, texture(dirt_albedo, d).rgb * 0.62, dirt);       // damp earth
	vec3 nor = mix(g_nor, texture(dirt_normal, d).rgb, dirt);
	vec3 arm = mix(g_arm, texture(dirt_arm, d).rgb, dirt);
	alb = mix(alb, texture(leaf_albedo, l).rgb * 0.75, leaves);
	nor = mix(nor, texture(leaf_normal, l).rgb, leaves);
	arm = mix(arm, texture(leaf_arm, l).rgb, leaves);

	ALBEDO = alb;
	NORMAL_MAP = nor;
	AO = arm.r;
	AO_LIGHT_AFFECT = 0.4;
	ROUGHNESS = clamp(arm.g, 0.5, 1.0);
	METALLIC = 0.0;
}
