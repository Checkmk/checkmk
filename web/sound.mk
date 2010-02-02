# Example for configuration of sounds in Multiadmin:

_sound_uri = "/nagios/media/"

multiadmin_sounds = {
  "host"     : _sound_uri + "explosion.wav", # host down or unreachable
  "critical" : _sound_uri + "arrow.wav",
  "warning"  : _sound_uri + "crawler.wav",
  "unknown"  : _sound_uri + "door.wav",
  "ok"       : _sound_uri + "tiktak.wav",
}

# Just as Nagios does it, only *one* sound is played on
# each page access, which reflects the "worst" event.
# The order is host -> critical -> warning -> unknown.
# If no problem exists, the "ok" sound is played.

# If one sound type is not defined in multiadmin_sounds,
# then no sound is played if that event is the worst
# one.
