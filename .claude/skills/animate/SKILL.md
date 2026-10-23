---
name: animate
description: Plan the scenes for a video and write its Manim animations (plan.md, video.toml, scenes.py) following design/DESIGN.md, then preview-render and check the stills visually. Use when a manuscript is ready to be animated, or animations need to be redone.
---

# Animate

Video: $ARGUMENTS

Run **Phase 2: Animate** from AGENTS.md, end to end.

1. `./pipeline status`; read `design/DESIGN.md`, the manuscript,
   `videos/example/scenes.py` (patterns), and the kit reference in AGENTS.md.
   If other videos in the series exist, reuse their recurring figures and
   colour roles.
2. Write the scene plan in `videos/<slug>/plan.md` first: classes, what
   happens on screen, cues, lengths, colour roles, handoffs. For a long or
   ambiguous manuscript, show the plan and wait for a yes before writing
   scenes.
3. Write `video.toml` (cue phrases from the manuscript, 3–5 words each) and
   `scenes.py`, following the scene rules in AGENTS.md.
4. `./pipeline check <slug>` until there are no errors or warnings.
5. `./pipeline preview <slug> -j 3`. Read every contact sheet in
   `build/<slug>/stills/` and go through the checklist in DESIGN.md
   section 8. Fix and preview again until every sheet is clean.
6. Update "Decisions to check", the Log and the Status line in plan.md.
7. Report: the scene table, the decisions to check, the preview file
   (`output/<slug>_480p15.mp4`), and recording instructions: one file per
   `*[Animasjon]*` marker, named `01_…`, `02_…`, in `videos/<slug>/audio/`,
   with half a second of silence at each end.
