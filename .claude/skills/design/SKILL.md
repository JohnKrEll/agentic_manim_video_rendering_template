---
name: design
description: Set up or change the visual design system for this video series (palette, colour roles, fonts, code display) in design/theme.py and design/DESIGN.md, and verify it on the example video. Use when the user describes how the videos should look.
---

# Design the series

Brief from the user: $ARGUMENTS

Run **Phase 0: Design** from AGENTS.md.

1. Read `design/DESIGN.md`, `design/theme.py` and, for a dark background,
   `design/examples/theme_dark.py`.
2. Turn the brief into tokens. If it gives only a few colours, derive the
   rest: `MUTED` (secondary text, readable on `BG`), `FAINT` (barely there),
   `CARD` (a step from `BG` towards white, or lighter on dark), `CARD_STROKE`,
   and `ON_ACCENT` (the text colour that reads best on the accents).
3. Decide what each accent *means* and write it in the palette table and
   the rules of section 1 in DESIGN.md. Keep sections 2–8 unless the brief
   asks for a different style; if it does, change the principles explicitly.
4. `./pipeline check example`, then `./pipeline preview example -j 3`, and
   Read every `build/example/stills/*_sheet.png`. Check the contrast of
   pills, highlights and muted text. Adjust `PILL_FILL`, `SOFT_FILL` and
   `HIGHLIGHT_OPACITY` if needed.
5. Report the palette with its roles, and point to two or three stills. Stop
   and wait for approval before animating anything with the new design.
