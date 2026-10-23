"""Design tokens: the one file to change for a new look.

Everything the kit (engine/kit.py) draws takes its colours, fonts and sizes
from here. The rules for *using* the tokens (what each colour means, motion,
layout) are in DESIGN.md next to this file. Keep the two in sync.

This is the light palette from the generics/testing videos: an off-white
background, a dark contrast colour, and two accents with fixed roles. The
accents are too light to read as text on the background, so they are used as
fills *behind* dark text ("pills" and highlights) and as strokes.

A dark alternative is in examples/theme_dark.py. Copy it over this file to
switch.
"""

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
BG = "#f7f5f0"  # background
FG = "#1d1d1f"  # text, code, arrows, strokes
ACCENT = "#f4a366"  # warm accent: the unknown / what needs attention / errors
ACCENT_2 = "#77c4b4"  # cool accent: the concrete / resolved / passing

MUTED = "#6e6e73"  # secondary text, code keywords
FAINT = "#b9b6ae"  # dimmed strokes, code comments, empty slots
CARD = "#fffdf9"  # code card background
CARD_STROKE = "#e2ded4"  # code card border
ON_ACCENT = FG  # text drawn on top of an accent fill

PILL_FILL = 0.55  # accent opacity behind a pill's text
SOFT_FILL = 0.3  # a quieter pill, for secondary labels: pill(..., fill=SOFT_FILL)
HIGHLIGHT_OPACITY = 0.6  # accent opacity behind highlighted code

# Semantic roles used by the kit's defaults (squiggle, status, Checklist).
OK = ACCENT_2
ERROR = ACCENT

# --------------------------------------------------------------------------
# Typography. The first installed font in each list wins.
# The code font must have no ligatures: CodeBlock maps characters to glyphs
# one by one, and a ligature merges two characters into one glyph.
# --------------------------------------------------------------------------
SANS_FONTS = ["Inter", "Cantarell", "Noto Sans", "DejaVu Sans", "Liberation Sans"]
MONO_FONTS = ["Source Code Pro", "Noto Sans Mono", "DejaVu Sans Mono", "Liberation Mono"]

TEXT_SIZE = 30  # body text
CODE_SIZE = 30  # code blocks
CAPTION_SIZE = 26  # the caption line at the bottom
HEADING_SIZE = 44  # headings / title cards

# --------------------------------------------------------------------------
# Code display. Keywords are drawn in MUTED so the accents stay free for the
# concept the video is about. Leave the video's main keyword *out* of this
# list (e.g. "where" in a video about constraints) so it keeps full contrast.
# --------------------------------------------------------------------------
CODE_KEYWORDS = (
    "public", "private", "protected", "internal", "static", "readonly",
    "class", "interface", "record", "struct", "var", "new", "get", "set",
    "void", "return", "if", "else", "for", "foreach", "while", "throw",
    "try", "catch", "using", "namespace", "async", "await",
)
CODE_COMMENT = r"//.*"  # regex for line comments (Python: r"#.*")
