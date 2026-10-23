"""A dark alternative to design/theme.py, with the same accents.

To use it: copy this file over design/theme.py, and update the palette table
in DESIGN.md. The scenes do not change.

On a dark background the roles of text and fill swap around: the accents
are bright enough to be read against, so pills get a stronger fill with
*dark* text on top, while highlights behind (light) code get weaker.
"""

BG = "#16171d"
FG = "#ecebe6"
ACCENT = "#f4a366"
ACCENT_2 = "#77c4b4"

MUTED = "#9a9aa3"
FAINT = "#585a64"
CARD = "#1f2129"
CARD_STROKE = "#33353f"
ON_ACCENT = "#16171d"

PILL_FILL = 0.92
SOFT_FILL = 0.7
HIGHLIGHT_OPACITY = 0.38

OK = ACCENT_2
ERROR = ACCENT

SANS_FONTS = ["Inter", "Cantarell", "Noto Sans", "DejaVu Sans", "Liberation Sans"]
MONO_FONTS = ["Source Code Pro", "Noto Sans Mono", "DejaVu Sans Mono", "Liberation Mono"]

TEXT_SIZE = 30
CODE_SIZE = 30
CAPTION_SIZE = 26
HEADING_SIZE = 44

CODE_KEYWORDS = (
    "public", "private", "protected", "internal", "static", "readonly",
    "class", "interface", "record", "struct", "var", "new", "get", "set",
    "void", "return", "if", "else", "for", "foreach", "while", "throw",
    "try", "catch", "using", "namespace", "async", "await",
)
CODE_COMMENT = r"//.*"
