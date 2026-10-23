---
name: manuscript
description: Give feedback on a video manuscript, or extend it, in the author's own voice (design/VOICE.md). Use when the user asks to evaluate, improve, extend or start a manuscript in videos/<slug>/manuscript.md.
---

# Manuscript

Video and request: $ARGUMENTS

Run **Phase 1: Manuscript** from AGENTS.md.

1. If there is no `videos/<slug>/`, create it: `./pipeline new <slug> --title "…"`.
2. Read `design/VOICE.md` first, then the manuscript. For context, read
   one or two other manuscripts in `videos/` (the author's actual voice).
3. **Feedback** (the default when the request is unclear): structure against
   "Shape of a video" in VOICE.md, correctness of the content and the code,
   consistency (dere, terms, names), and whether every `*[Animasjon: …]*`
   marker describes something drawable and starts a sensible recording.
   Give numbered, concrete suggestions with line references, and a rewritten
   sentence where wording is the point. Don't edit the file.
4. **Extending** (only when asked): edit the file in the author's voice and
   summarise what is new, so the author can review it.
5. When the author rewrites one of your suggestions, ask whether to add the
   pattern to `design/VOICE.md`, and add it if they agree.
6. Stop. The author approves the manuscript before `/animate`.
