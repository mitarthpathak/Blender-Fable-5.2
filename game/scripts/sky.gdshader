// The town's sky (scripts/lighting_presets.gd sets it up outdoors and feeds
// it each look's values; the house world keeps its plain background).
//
// - A gradient from the horizon up, with the fog's colour in a haze band at
//   the horizon so the sky meets the distance fog without a seam.
// - One layer of cloud on a plane overhead, from a tileable noise at four
//   sizes. It drifts with `drift` (moved by the script, not TIME, so the
//   reflection cubemap only updates a little at a time). The side of each
//   cloud towards the sun or moon is lit, the far side shaded, and thin edges
//   glow when looking towards the light.
// - The sun's disc and glow by day; the moon with its markings and a halo by
//   night; stars in the gaps between clouds. The light behind thick cloud
//   still shows as a brighter patch.
// - At night an orange glow low on the horizon: the town's sodium lights on
//   the cloud base.
//
// Clouds and gradient are worked out at half resolution (soft anyway); the
// discs and stars are added at full resolution so they stay sharp. The
// reflection cubemap gets the clouds but no discs or stars: the lights' own
// highlights already do that on wet surfaces.
shader_type sky;
render_mode use_half_res_pass;

uniform sampler2D noise_tex : filter_linear_mipmap, repeat_enable;
uniform vec3 top_color : source_color = vec3(0.22, 0.38, 0.66);
uniform vec3 horizon_color : source_color = vec3(0.62, 0.7, 0.8);
uniform vec3 haze_color : source_color = vec3(0.6, 0.65, 0.7);
uniform float haze_height = 0.12;
uniform float haze_amount = 0.85;

uniform float cloud_cover : hint_range(0.0, 1.0) = 0.5;
uniform vec3 cloud_lit : source_color = vec3(1.0, 0.97, 0.92);
uniform vec3 cloud_shade : source_color = vec3(0.5, 0.53, 0.58);
uniform float cloud_scale = 0.55;
uniform float cloud_softness = 0.17;
uniform vec2 drift = vec2(0.0);

uniform float light_glow = 0.5;        // the soft brightness round the sun or moon
uniform float sun_disc = 1.0;          // 0..1
uniform float moon_disc = 0.0;         // 0..1
uniform float sun_size = 1.6;          // degrees across, as drawn (bigger than life, as games do)
uniform float moon_size = 2.6;
uniform float stars = 0.0;             // 0..1
uniform vec3 town_glow : source_color = vec3(0.0);
uniform float sky_time = 0.0;          // seconds, for the stars' twinkle

float hash13(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.zyx + 31.32);
	return fract((p.x + p.y) * p.z);
}

vec3 hash33(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.xxy + p.yxx) * p.zyx);
}

float fbm(vec2 p) {
	float f = texture(noise_tex, p + drift).r * 0.5;
	f += texture(noise_tex, p * 2.03 + drift * 1.4 + vec2(0.17, 0.31)).r * 0.25;
	f += texture(noise_tex, p * 4.01 + drift * 2.1 + vec2(0.53, 0.07)).r * 0.15;
	f += texture(noise_tex, p * 8.13 + drift * 2.9 + vec2(0.29, 0.71)).r * 0.1;
	return f;
}

// Gradient, haze and clouds. Returns the colour and how much cloud covers it.
vec4 base_sky(vec3 d, vec3 l, vec3 l_col, float l_energy) {
	float up = clamp(d.y, 0.0, 1.0);
	vec3 col = mix(horizon_color, top_color, pow(up, 0.45));

	// the light's glow (stronger along the horizon when it is low)
	float to_light = max(dot(d, l), 0.0);
	vec3 glow = l_col * l_energy * light_glow * (0.06 * pow(to_light, 4.0) + 0.25 * pow(to_light, 32.0));
	col += glow;

	// clouds on a plane overhead; they flatten and thin out towards the horizon
	float fade = smoothstep(0.015, 0.2, d.y);
	float cover = 0.0;
	if (fade > 0.0 && cloud_cover > 0.0) {
		vec2 p = d.xz / (d.y + 0.12) * cloud_scale;
		p += (texture(noise_tex, p * 0.21 + drift * 0.5 + vec2(0.61, 0.13)).rg - 0.5) * 0.1;
		float f = fbm(p);
		// more cloud in some parts of the sky than others: clear gaps and thicker banks
		float banks = texture(noise_tex, p * 0.16 - drift * 0.2 + vec2(0.37, 0.83)).r;
		float local_cover = clamp(cloud_cover + (banks - 0.5) * 0.9 * (1.0 - cloud_cover * cloud_cover), 0.0, 1.0);
		float edge = 1.0 - local_cover;
		cover = smoothstep(edge - cloud_softness, edge + cloud_softness, f) * fade;
		// lit side: the cloud thins towards the light
		vec2 towards = normalize(l.xz + vec2(1e-4)) * 0.035;
		float f_l = fbm(p + towards);
		float lit = clamp(0.55 + (f - f_l) * 6.0, 0.0, 1.0);
		float thick = smoothstep(edge, edge + 0.35, f);
		vec3 c = mix(cloud_lit, cloud_shade, mix(thick * 0.8, 1.0 - lit, 0.5));
		// thin edges glow when looking towards the light
		c += l_col * l_energy * light_glow * pow(to_light, 6.0) * (1.0 - thick) * 0.6;
		col = mix(col, c, cover);
		// the sun or moon behind the cloud still shows as a brighter patch
		col += l_col * l_energy * light_glow * (0.05 * pow(to_light, 6.0) + 0.12 * pow(to_light, 40.0)) * cover;
	}

	// the town's lights on the haze and the cloud base, all round the horizon
	col += town_glow * exp(-up * 9.0) * (0.6 + 0.4 * cover);
	// the fog's colour along the horizon, so the sky meets the distance fog
	col = mix(col, haze_color, haze_amount * (1.0 - smoothstep(0.0, haze_height, d.y)));
	if (d.y < 0.0) {
		col = haze_color * 0.9;
		cover = 1.0;
	}
	return vec4(col, cover);
}

void sky() {
	vec3 d = EYEDIR;
	vec3 l = LIGHT0_ENABLED ? LIGHT0_DIRECTION : vec3(0.0, 1.0, 0.0);
	vec3 l_col = LIGHT0_ENABLED ? LIGHT0_COLOR : vec3(0.0);
	float l_energy = LIGHT0_ENABLED ? min(LIGHT0_ENERGY, 3.0) : 0.0;

	if (AT_CUBEMAP_PASS || AT_HALF_RES_PASS) {
		vec4 s = base_sky(d, l, l_col, l_energy);
		COLOR = s.rgb;
		ALPHA = s.a;
	} else {
		vec3 col = HALF_RES_COLOR.rgb;
		float cover = clamp(HALF_RES_COLOR.a, 0.0, 1.0);
		float clear = 1.0 - cover;
		float cos_a = dot(d, l);
		float r = radians(sun_size) * 0.5;
		float rm = radians(moon_size) * 0.5;
		float ang = acos(clamp(cos_a, -1.0, 1.0));

		// the sun: a hot disc with a soft rim; through cloud only a glow is left
		if (sun_disc > 0.0) {
			float disc = 1.0 - smoothstep(r * 0.85, r, ang);
			col += l_col * disc * sun_disc * 18.0 * clear * clear;
			col += l_col * sun_disc * 0.4 * exp(-ang / (r * 3.0)) * mix(0.35, 1.0, clear);
		}
		// the moon: grey markings, darker towards its rim, a halo in the haze
		if (moon_disc > 0.0) {
			vec3 t = normalize(cross(l, abs(l.y) < 0.99 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0)));
			vec3 b = cross(t, l);
			vec2 uv = vec2(dot(d, t), dot(d, b)) / rm;
			float rr = dot(uv, uv);
			if (rr < 1.2) {
				float disc = 1.0 - smoothstep(0.92, 1.0, sqrt(rr));
				float maria = texture(noise_tex, uv * 0.18 + vec2(0.31, 0.47)).r;
				float albedo = mix(0.62, 1.0, smoothstep(0.42, 0.62, maria)) * (1.0 - 0.25 * rr);
				col = mix(col, vec3(0.92, 0.95, 1.0) * albedo * 2.4, disc * moon_disc * clear);
			}
			col += vec3(0.75, 0.82, 1.0) * moon_disc * 0.18 * exp(-ang / (rm * 5.0)) * mix(0.5, 1.0, clear);
		}
		// stars: fixed points on the sky sphere, fainter low down and near the moon
		if (stars > 0.0 && d.y > 0.0) {
			vec3 q = d * 300.0;
			vec3 id = floor(q);
			float h = hash13(id);
			if (h > 0.972) {
				vec3 at = id + 0.5 + (hash33(id) - 0.5) * 0.6;
				float dist = length(q - at);
				float size = mix(0.16, 0.3, fract(h * 91.7));
				float s = smoothstep(size, 0.0, dist);
				float twinkle = 0.75 + 0.25 * sin(sky_time * (2.0 + 5.0 * fract(h * 37.3)) + h * 60.0);
				float mag = pow(fract(h * 53.1), 3.0) * 2.4 + 0.3;
				float low = smoothstep(0.04, 0.35, d.y);
				float near_moon = 1.0 - moon_disc * exp(-ang / 0.25);
				vec3 tint = mix(vec3(1.0, 0.86, 0.72), vec3(0.78, 0.86, 1.0), fract(h * 13.7));
				col += tint * s * mag * twinkle * stars * low * near_moon * clear * clear;
			}
		}
		COLOR = col;
	}
}
