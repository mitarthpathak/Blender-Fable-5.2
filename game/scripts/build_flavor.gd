class_name BuildFlavor
## Which build this is, and the defaults that go with it.
##
## The "Halden Ridge Day" export preset sets the feature tags "town" and
## "dayroam". That build starts in the town world with the player inside the
## house, at 10:00 in clear weather, on Low quality. They are defaults
## only: F1, F2 and F4 still change them, and what the player picks is kept in
## the day build's own settings file, so an older build's saved Night or High
## cannot override the first start.
##
## From the editor or the command line, `-- --flavor=day` does the same as the
## feature tag.


static func is_day() -> bool:
	return OS.has_feature("dayroam") or "--flavor=day" in OS.get_cmdline_user_args()


## "town" or "house", before any --world= argument.
static func world() -> String:
	return "town" if OS.has_feature("town") or is_day() else "house"


static func settings_file() -> String:
	return "user://settings_day.cfg" if is_day() else "user://settings.cfg"


static func default_quality() -> String:
	return "low" if is_day() else "high"


static func default_preset() -> String:
	return "1000_clear" if is_day() else "0300_foggy"      # ids from scripts/lighting_presets.gd


static func name() -> String:
	return "day" if is_day() else ("town" if OS.has_feature("town") else "house")
