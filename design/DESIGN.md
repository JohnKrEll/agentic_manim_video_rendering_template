# Design document

The visual rules every scene follows. The *values* live in
[`theme.py`](theme.py) and the building blocks in
[`../engine/kit.py`](../engine/kit.py); this document says how to use them.

For a new series, change the palette table and `theme.py` together. The
principles below the palette came out of the generics, testing and ASP.NET
videos and work for any subject. Change them only on purpose.

## 1. Palette and colour roles

| Token         | Value     | Role                                                                 |
| ------------- | --------- | -------------------------------------------------------------------- |
| `BG`          | `#f7f5f0` | Background (off-white)                                               |
| `FG`          | `#1d1d1f` | Text, code, arrows, strokes                                          |
| `ACCENT`      | `#f4a366` | Warm: the unknown or general (`T`), what needs attention, errors     |
| `ACCENT_2`    | `#77c4b4` | Cool: the concrete or filled in (`string`, `int`), resolved, passing |
| `MUTED`       | `#6e6e73` | Captions, secondary text, code keywords                              |
| `FAINT`       | `#b9b6ae` | Dimmed strokes, comments, empty slots                                |
| `CARD`        | `#fffdf9` | Code card background                                                 |
| `CARD_STROKE` | `#e2ded4` | Code card border                                                     |

Rules:

- **The accents are surfaces, not text.** They are too light to read on the
  background, so they go *behind* dark text (`pill`, `highlight`) or are used
  as strokes (`squiggle`, underlines). Text on an accent uses `ON_ACCENT`.
- **One meaning per colour per video.** The default is warm = "unknown /
  attention / wrong" and cool = "concrete / resolved / right". A video may
  remap them (the testing video used cool = passes, warm = fails). Write the
  remap in the video's `plan.md` and keep it for the whole video.
- **Use the tokens, never hex values or fixed opacities in scenes.** Use
  `PILL_FILL`, `SOFT_FILL` and `HIGHLIGHT_OPACITY` (the defaults), so a
  re-skin (e.g. `examples/theme_dark.py`) works without touching the scenes.

## 2. Typography

- **Sans** (`label`, `heading`, `Caption`) for words. **Mono** (`CodeBlock`,
  `mono`, pills) for code and names from code.
- The code font must have **no ligatures** (Source Code Pro). `CodeBlock`
  raises an error if the glyph count doesn't match the characters.
- Sizes: title card 72–76, heading 38–44, body 26–32, code 22–36 (bigger for
  fewer lines), caption 26.
- On-screen text is in the narration's language. Code stays as code.
- No LaTeX: use `Text` (via the kit), never `Tex`/`MathTex`.

## 3. The frame

Manim's frame is 14.2 × 8 units with (0, 0) in the centre.

- **The caption line is reserved:** y = −3.45, bottom centre. Nothing else
  goes below y ≈ −2.9.
- Content lives within x ±6.6 and y −2.9 … 3.4, at least 0.3 from the edge.
  `CodeBlock` scales itself down to 12.6 wide.
- **No permanent title.** A heading may open a scene, or a title card may
  open the video, but after that the whole frame is for the content. (The
  first ASP.NET version kept a title on screen all the time. That shrank the
  code and the map and caused clipping.)
- One main idea on screen at a time. Clear what is done before the next
  thing arrives.

## 4. Motion

What makes the style feel snappy:

- **Change things in place.** `morph_code` turns one code block into
  another token by token; a class header changes while the body stays; a
  box *becomes* the next figure. Avoid "fade everything out, fade something
  new in" as the default transition.
- **Something happens on every cue.** When the narration lists things, each
  item appears or pulses as it is named (give each its own cue). No picture
  should stand still for more than about 8–10 seconds of speech.
- **Point without recolouring:** `pulse(m)` or `Indicate(m)`. Colour means
  something (section 1), so don't use it just for emphasis.
- **Durations:** most animations 0.4–1.2 s, morphs 1.3–1.8 s, groups with
  `LaggedStart(..., lag_ratio=0.2–0.35)`. Play a caption change *together
  with* the picture change it describes.
- **An animation must finish before the next cue.** If it doesn't, the
  render prints `[timing] … late`; shorten `run_time` or move work after
  the cue.
- **Invisible cuts.** When one scene leads straight into the next, scene N
  ends on exactly the picture scene N+1 starts with. Build that picture in a
  shared function, end scene N with `until_end(...)` plus fading out only
  the extras, and start scene N+1 by `add`ing the same objects.
- **Bookends.** The summary may return to the opening picture (the generics
  intro ends where it began, with `List<T>` over the two lists).
- Every scene ends with `self.finish()` (fade out at the end of its audio)
  or a handoff as above.

## 5. Captions

- Short: names, values and the point, ideally under 60 characters. **Don't
  repeat the narration word for word.**
- After recording, match the wording to what was actually *said*.
- State things directly. No "ikke X, men Y" / "not X, but Y" framings and no
  dash punchlines ("Ikke et drept program — en kontrollert nedstenging").
  See [`VOICE.md`](VOICE.md).

## 6. Code on screen

- Always a `CodeBlock`, so tokens can be found (`find`), highlighted
  (`highlight`, `highlights`, `line_highlight`), dimmed (`dim_rest`) and
  morphed (`morph_code`).
- Keywords are drawn muted (`CODE_KEYWORDS`); the accents are reserved for
  the concept. **Leave the video's main keyword out of the list** (in the
  constraints video `where` kept full contrast).
- Fold what doesn't matter (`{ … }`, a loop without braces) so the relevant
  code fits at a readable size. A shortened version in the scene is fine
  when the manuscript has the full one; note it under "Decisions to check".
- Compiler errors: `squiggle` under the code in `ERROR`, plus the error text
  as a caption or an `overlay`.

## 7. Recurring figures

A figure that comes back gives viewers something to hold on to: the
container in the generics videos, the checklist in the testing video, the
architecture map in the ASP.NET series. Build it once (a function or a
`VGroup` subclass in the scene file, or in the kit if several videos use it),
give it animations for its states (`Checklist.mark`, `reset`, `relabel`),
and reuse it in the opening, the middle and the summary.

## 8. Checking the stills

`./pipeline preview <video>` writes one contact sheet per scene to
`build/<video>/stills/`. Check every sheet for:

- [ ] nothing clipped at the frame edges (pills placed "next to" a wide card
      are the usual culprit)
- [ ] nothing overlaps the caption line, and captions fit on one line
- [ ] highlights sit exactly behind the intended tokens
- [ ] text is readable at 480p
- [ ] no leftovers after a fade, and no frame with an empty stage for long
- [ ] handoffs: the `last` frame of scene N matches the `start` frame of N+1
- [ ] the colour roles are used the same way throughout
