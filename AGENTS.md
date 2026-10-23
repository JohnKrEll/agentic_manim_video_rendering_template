# Agent playbook: Manim explainer videos

You help an author turn a manuscript into a finished, voice-synced Manim
video. The author writes and records; you design, animate, sync, render
and check. `README.md` explains the process for humans; this file is how
*you* run it.

## Start of every session

1. `./pipeline status`: one line per video, with its next step.
2. Read the **Status** line and the Log in `videos/<slug>/plan.md` for the
   video in question.
3. Re-read `design/DESIGN.md` before animating and `design/VOICE.md` before
   touching a manuscript. They change between sessions.

## Ground rules

- **The author owns the words.** Never rewrite `manuscript.md` without being
  asked. When asked to extend or improve it, follow `design/VOICE.md`,
  mirror the author's sentences, and say what you changed. When the author
  corrects your wording, add the rule to `VOICE.md`.
- **Stop at the gates** (marked ⛔ below) and wait for the author.
- **Verify before you report.** Say a video is in sync only after
  `assemble` printed matching picture and sound lengths. Say a layout is
  right only after looking at the stills. If something was skipped or
  failed, say so.
- **Keep `plan.md` current:** the Status line, Decisions to check, and a
  dated Log entry for each session. It is how the next session picks up.
- **Long commands take minutes** (`transcript`/`sync` the first time,
  `render -q h`, `build`). Run them in the background if your tools allow,
  and don't start a second render of the same video meanwhile.
- **Don't edit** `engine/` or `design/theme.py` as part of making one video.
  Improve the engine or design only when asked, and then for all videos.

## Where things are

| Path                         | What                                   | You edit it?                  |
| ---------------------------- | -------------------------------------- | ----------------------------- |
| `design/DESIGN.md`, `theme.py` | Visual rules and tokens              | Phase 0 only                  |
| `design/VOICE.md`            | The author's voice                     | When the author corrects you  |
| `project.toml`               | Language, Whisper, recording order     | Rarely                        |
| `videos/<slug>/manuscript.md`| The author's text                      | Only when asked               |
| `videos/<slug>/plan.md`      | Scene plan, decisions, status, log     | Yes, always                   |
| `videos/<slug>/video.toml`   | Scenes in order + cue phrases          | Yes                           |
| `videos/<slug>/scenes.py`    | The Manim scenes                       | Yes                           |
| `videos/<slug>/audio/`       | The author's recordings                | Never                         |
| `videos/example/`            | Reference implementation               | No; read it for patterns      |
| `build/`, `output/`          | Generated                              | No (safe to delete)           |

## Phase 0: Design (once per series)

From the author's brief (colours, mood, subject):

1. Set the tokens in `design/theme.py`: `BG`, `FG`, two accents, `MUTED`,
   `FAINT`, `CARD`, `CARD_STROKE`, `ON_ACCENT`, the fill/opacity tokens,
   fonts and `CODE_KEYWORDS`/`CODE_COMMENT` for the language shown. On a dark
   background start from `design/examples/theme_dark.py`.
2. Update the palette table and colour roles in `design/DESIGN.md`. Keep
   sections 2–8 unless the author wants a different style.
3. Render `./pipeline preview example` and look at the sheets: contrast of
   pills and highlights, legibility of muted text.
4. ⛔ Show the author two or three stills and the colour roles.

## Phase 1: Manuscript

1. `./pipeline new <slug> --title "…"` if the folder doesn't exist.
2. Feedback: check structure (see "Shape of a video" in `VOICE.md`),
   correctness of the content and code, consistency (du/dere, terms),
   and that each `*[Animasjon: …]*` marker describes something that can be
   drawn. Give concrete suggestions with line references.
3. Extending: write in the author's voice and mark what is new.
4. ⛔ The author approves (and usually rewrites parts of) the manuscript.

## Phase 2: Animate

1. **Plan** in `plan.md`: one scene per marker or section (split long
   ones), with class name, manuscript part, what happens on screen, cues,
   estimated length (~150 words of speech per minute). Note colour roles,
   handoffs between scenes, and a recurring figure if there is one.
2. **Cue map** in `video.toml`: scenes in order; `start` = the first words
   of each scene after the first; one cue per change on screen, phrase =
   the first 3–5 words of the sentence it should hit, taken from the
   manuscript. When the narration lists things, give each item a cue.
3. **Scenes** in `scenes.py` (rules below; copy patterns from
   `videos/example/scenes.py`).
4. `./pipeline check <slug>`: no errors; resolve warnings.
5. `./pipeline preview <slug> -j 3`, then **read every contact sheet** in
   `build/<slug>/stills/<Scene>_sheet.png` against the checklist in
   `DESIGN.md` section 8. Fix and repeat until clean.
6. Fill in "Decisions to check" (shortened code, invented examples,
   captions that go beyond the manuscript).
7. ⛔ Report: the scene table, the decisions, and where the preview is
   (`output/<slug>_480p15.mp4`). Tell the author how to record: one file
   per marker, `01_…`, `02_…`, in `videos/<slug>/audio/`.

### Scene rules

- One class per scene, deriving from `TimedScene`, listed in `video.toml`
  in order. The import line at the top of the skeleton must stay.
- Wait for the narration with `self.cue("name", fallback=s)`, where `s` is
  your estimate of the seconds of speech since the previous cue. Every name
  must be in that scene's `[scenes.cues]`, and every cue there must be used.
- Play the caption change together with the picture change:
  `self.play(FadeIn(x), c.say("…"), run_time=0.8)`.
- End with `self.finish(fallback=…)`, or for a handoff:
  `self.until_end(0.7, fallback=…)` then fade out only the extras. The next
  scene starts by `add`ing the same picture, built by a shared function.
- Use theme tokens and kit defaults; no hex colours, no fixed opacities.
- No `Tex`/`MathTex` (no LaTeX installed). Use `label`, `mono`, `Text`.
- Code is always a `CodeBlock`. `find()` raises if the pattern is missing:
  that is a typo, not something to catch.
- Fills sit behind text: `card_around` has z −2, highlights z −1, overlays
  z 5+. The `Caption` is a foreground object and always on top.
- Keep content inside x ±6.6, y −2.9 … 3.4. Nothing near the caption line.

### Kit reference (`engine/kit.py`, imported with `from kit import *`)

| Name | Use |
| ---- | --- |
| `TimedScene` | Base class. `cue(name, fallback)`, `until_end(run_time, fallback)`, `finish(fallback, run_time)`, `timed` |
| `Caption(scene)` | Bottom caption line. `say(text)` and `clear()` return animations |
| `label(t, size, color)`, `mono(t, size, color)` | Sans / code-font text |
| `heading(t, subtitle)` | Heading at the top, for title cards and scene openers |
| `pill(t, color, size, fill)` | Text on an accent surface; `fill=SOFT_FILL` for quieter ones |
| `card_around(m)`, `overlay(content)` | Card behind something; a card on top of the picture |
| `arrow(a, b)`, `pulse(m)`, `squiggle(m)` | Arrow; point at something; compiler-error underline |
| `status(ok)`, `empty_status()`, `Checklist(title, items)` | ✓/✗ marks; a checklist with `mark(i, ok)`, `reset()`, `relabel(items)` |
| `CodeBlock(src, size, frame)` | Code. `find(p)` → list of glyph groups, `line(i)`, `highlight(g, color)`, `highlights(p)`, `line_highlight(i)`, `dim_rest(keep)`, `.text`, `.frame` |
| `morph_code(scene, a, b, extra, frame_from, run_time)` | Animate code block `a` into `b` token by token; plays it and leaves `b` in the scene |
| Tokens | `BG FG ACCENT ACCENT_2 MUTED FAINT CARD CARD_STROKE ON_ACCENT OK ERROR PILL_FILL SOFT_FILL HIGHLIGHT_OPACITY SANS MONO` |

## Phase 3: Recording (the author)

Wait. Nothing to do until the files are in `videos/<slug>/audio/`.

## Phase 4: Sync, render, assemble

1. `./pipeline transcript <slug>` (first time: minutes). Read
   `build/<slug>/transcript.md` next to the manuscript:
   - Did the author say each cue phrase? Whisper's spelling counts
     ("Verden" for "verten", "bild" for "Build", "supersimpel").
   - Wording the author changed while recording: update cue phrases, and
     captions that quote the narration.
   - Lines nobody said (subtitle credits in silence): add their start to
     `drop_phrases`.
   - Possible stumbles or false starts (repeated words): note the time
     and file and tell the author; don't cut audio yourself.
   - Odd written standard (Nynorsk forms, wrong language): improve
     `vocabulary`, written as a sentence in the right standard.
2. `./pipeline sync <slug>`. On `did not find`, use the closest match and
   context in the error to fix the phrase. Use `--fuzzy` only to get
   unstuck, then write the matched words into `video.toml`.
3. Check the printed cue table: each cue's words should be the moment you
   meant. Adjust with another phrase or `offset`.
4. `./pipeline render <slug> -j 3` (1080p60). Fix every `[timing] … late`
   (shorten `run_time` before that cue), `never waited for`, and
   `runs past its audio`; render again.
5. `./pipeline assemble <slug>`. Picture and sound must match (± 0.1 s).
6. `./pipeline stills <slug> -q h` and read the sheets once more.
7. Log the changes in `plan.md` and set the Status line.
8. ⛔ Report: the file, its length and size, the picture/sound check, the
   number of cues hit, the phrases and captions you changed to match the
   recording, and anything the author should listen for.

## Phase 5: Feedback

Map each remark onto the cue map or the scene: "X should come on Y" → cue
phrase; "too static" → more cues and motion during lists; "caption is
wrong" → caption text. Then `sync` (if `video.toml` changed), `render`
(only the affected scenes are slow; Manim caches the rest), `assemble`,
stills, report.

## Reading the pipeline's output

| Output | Meaning |
| ------ | ------- |
| `✗ … waits for cue 'x', which is not in video.toml` | Add the cue or fix the name |
| `! … cue 'x' in video.toml is never waited for` | Use it or remove it |
| `did not find «…»` + `Closest: «…»` | Phrase differs from what Whisper heard |
| `[timing] Scene: «cue» 1.2 s late` | Animations before the cue are too long |
| `[timing] Scene: runs 2.0 s past its audio` | Missing `finish()`/`until_end()` at the end |
| `Rendered with older timing: A, B` | Render A and B again after a sync |
| `picture 70.65 s, sound 70.65 s` | In sync |
| `next` column in `status` | The next step for each video |
