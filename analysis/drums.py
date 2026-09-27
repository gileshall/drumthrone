"""GM percussion map (notes 35-81) grouped into kit categories."""

NAMES = {
    35: "Acoustic Bass Drum", 36: "Bass Drum 1", 37: "Side Stick", 38: "Acoustic Snare",
    39: "Hand Clap", 40: "Electric Snare", 41: "Low Floor Tom", 42: "Closed Hi-Hat",
    43: "High Floor Tom", 44: "Pedal Hi-Hat", 45: "Low Tom", 46: "Open Hi-Hat",
    47: "Low-Mid Tom", 48: "Hi-Mid Tom", 49: "Crash Cymbal 1", 50: "High Tom",
    51: "Ride Cymbal 1", 52: "Chinese Cymbal", 53: "Ride Bell", 54: "Tambourine",
    55: "Splash Cymbal", 56: "Cowbell", 57: "Crash Cymbal 2", 58: "Vibraslap",
    59: "Ride Cymbal 2", 60: "Hi Bongo", 61: "Low Bongo", 62: "Mute Hi Conga",
    63: "Open Hi Conga", 64: "Low Conga", 65: "High Timbale", 66: "Low Timbale",
    67: "High Agogo", 68: "Low Agogo", 69: "Cabasa", 70: "Maracas",
    71: "Short Whistle", 72: "Long Whistle", 73: "Short Guiro", 74: "Long Guiro",
    75: "Claves", 76: "Hi Wood Block", 77: "Low Wood Block", 78: "Mute Cuica",
    79: "Open Cuica", 80: "Mute Triangle", 81: "Open Triangle",
}

# Display order runs low to high register; "other" holds notes outside 35-81.
CATEGORIES = {
    "kick": (35, 36),
    "snare": (37, 38, 40),
    "toms": (41, 43, 45, 47, 48, 50),
    "hi-hat": (42, 44, 46),
    "ride": (51, 53, 59),
    "crash": (49, 52, 55, 57),
    "aux": (39, 54, 56, 58, *range(60, 82)),
    "other": (),
}
CATEGORY = {n: c for c, ns in CATEGORIES.items() for n in ns}

# Okabe-Ito hues, fixed per category everywhere.
COLORS = {
    "kick": "#0072B2", "snare": "#D55E00", "toms": "#E69F00", "hi-hat": "#009E73",
    "ride": "#56B4E9", "crash": "#CC79A7", "aux": "#4D4D4D", "other": "#A6A6A6",
}

FEET = {35, 36, 44}  # kick and hi-hat pedal; every other note needs a hand

# Audio band each category is measured in when estimating per-hit level.
BAND_OF = {"kick": "low", "snare": "mid", "toms": "mid", "aux": "mid", "other": "mid",
           "hi-hat": "high", "ride": "high", "crash": "high"}


def category(note):
    return CATEGORY.get(note, "other")


def name(note):
    return NAMES.get(note, f"Note {note}")
