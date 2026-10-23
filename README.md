# Manim video template

A reusable setup for making explainer videos with an AI agent: you write
and record the manuscript, the agent animates it in [Manim](https://www.manim.community/)
and times every animation to your voice, and a script assembles the
finished video.

It is the process behind the generics, testing and ASP.NET Core videos,
cleaned up so that it works for any subject and any visual design.

```
 you                          agent                          scripts
 ───                          ─────                          ───────
 1  design brief  ───────────▶ design/DESIGN.md + theme.py
 2  manuscript    ◀──────────▶ feedback in your voice
                               (design/VOICE.md)
 3                             scene plan + scenes.py  ────▶ preview: render 480p,
    check the plan ◀────────── stills checked by eye          stills per cue
 4  record, one file
    per marker    ───────────────────────────────────────▶  transcribe (Whisper)
 5                             cue phrases fixed to what ◀── sync: find every cue
                               you actually said              in your speech
 6                             ─────────────────────────────▶ render 1080p60,
                                                              assemble the .mp4
 7  watch, give feedback ────▶ adjust, re-sync, re-render
```

## Contents

- [Quick start](#quick-start)
- [The process, step by step](#the-process-step-by-step)
- [Recording](#recording)
- [The cue map](#the-cue-map)
- [Giving feedback](#giving-feedback)
- [Changing the design, or starting a new series](#changing-the-design-or-starting-a-new-series)
- [Working with Claude](#working-with-claude)
- [Commands](#commands)
- [Folders](#folders)
- [Troubleshooting](#troubleshooting)

## Quick start

You need `ffmpeg`, Python 3.11 or newer, and about 4 GB of disk for the
Whisper model.

```bash
./setup.sh               # .venv with Manim + faster-whisper, checks fonts
./pipeline status        # where every video is
./pipeline build example # the smoke test: transcribe, sync, render, assemble
```

`build example` makes `output/example.mp4`, a 70-second excerpt of the
generics intro with its original recording. The first run downloads the
Whisper model (~3 GB) and takes a few minutes. If it works, everything
works.

On this machine `.venv` is a link to the venv in
`AspNetCoreWebApi/animations/`, which already has everything installed. To
reuse a venv elsewhere: `./setup.sh --link /path/to/venv`.

## The process, step by step

Each step says who does what. The agent stops at the end of steps 1–3 and
waits for you.

### 1. Design (once per series)

Decide how the videos should look: a background, a dark contrast colour, one
or two accent colours, and what each colour *means*. The agent writes the
values into `design/theme.py` and the rules into `design/DESIGN.md`.

> "Use an off-white background, #f4a366 and #77c4b4 as accents, #1d1d1f as the dark contrast colour."

The existing design document already holds the lessons from the earlier
videos (no permanent title, change things in place, something happens on
every cue). Keep those unless you want a different style.

### 2. Manuscript

`./pipeline new <slug> --title "..."` creates `videos/<slug>/`. Write the
manuscript in `manuscript.md`, the way you will say it:

~~~markdown
*[Animasjon: Klassene skrives ut én etter én. Datatypene markeres med farge.]*
Se hva som skjer hvis vi prøver å lage en slik beholder uten generics:
```csharp
public class StringContainer { public string Value { get; set; } }
```
Legg merke til at disse tre klassene er helt like, bortsett fra datatypen.
~~~

- An **animation marker** `*[Animasjon: …]*` starts a new picture. It is
  also where you start a new recording.
- **Code blocks** are what is shown on screen, not read aloud.
- `<!-- comments -->` are notes to yourself.

Ask the agent for feedback, or to extend a draft. It follows
`design/VOICE.md`, which describes your voice (direct statements, "dere",
"Legg merke til …", "Så, kort oppsummert: …"). When you rewrite one of its
suggestions, tell it to add the rule to `VOICE.md`, so the next video
starts from it.

### 3. Animation

The agent splits the manuscript into scenes and writes the plan into
`videos/<slug>/plan.md`: one row per scene, with what happens on screen,
the cues and the colour roles. Then it writes the scenes in `scenes.py` and
the cue map in `video.toml`.

It checks its own work by rendering a preview and looking at the stills:
one picture per cue, gathered on a contact sheet per scene in
`build/<slug>/stills/`. You can watch the silent preview in
`output/<slug>_480p15.mp4`.

Read the **"Decisions to check"** section of `plan.md`: shortened code,
invented examples, and things the manuscript didn't specify.

### 4. Recording

Record one file per animation marker. See [Recording](#recording).

### 5. Sync

The agent runs `./pipeline transcript <slug>` and compares what Whisper
heard with the cue phrases. Whisper sometimes hears a word differently
("verten" as "Verden", "kjeden" as "skjeden"), and you sometimes say
something slightly different from the manuscript. The agent updates the
phrases in `video.toml`, and the captions too where they should follow your
actual words. Then `./pipeline sync <slug>` finds every cue in your speech
and cuts one audio clip per scene.

### 6. Render and assemble

`./pipeline build <slug>` (or `render` then `assemble`) renders every
scene at 1080p60 with its own audio clip, and joins everything into
`output/<slug>.mp4`. The last line shows the picture and sound lengths, and
they should be equal. Since every scene has its own clip, sound and picture
line up again at every scene boundary, so a scene that runs a frame long
never shifts the rest of the video.

### 7. Review

Watch the video and say what to change. See [Giving feedback](#giving-feedback).

## Recording

- **One file per animation marker**, from top to bottom.
- **Name the files with a number first:** `01_list_string.wav`,
  `02_tre_klasser.wav`… They are joined in name order, so a re-take of file
  3 simply replaces `03_….wav`. (`recordings = "recorded"` in `video.toml`
  uses the order the files were written instead.)
- WAV or FLAC is best; MP3, M4A and OGG work too.
- Leave about half a second of silence at the start and end. The silence
  is trimmed down to a short breath (`head`/`tail` in `project.toml`).
- Put them in `videos/<slug>/audio/`.
- You don't have to stick to the manuscript word for word. The sync
  follows what you actually said.
- A stumble or false start: re-record that file. Only that stretch is
  transcribed again.

## The cue map

`videos/<slug>/video.toml` lists the scenes in order and, for each scene,
the phrases its animations wait for:

```toml
[[scenes]]
name = "WithoutGenerics"          # the class in scenes.py
start = "se hva som skjer"         # the first words of the scene
  [scenes.cues]
  identical = "legg merke til at disse tre"
  rule = "hvis vi vil endre en regel"
  merge = { phrase = "for å hjelpe med dette", offset = 0.4 }
```

In the scene, `self.cue("rule", fallback=2.4)` waits until "hvis vi vil
endre en regel" is said, then the next animation plays. Before anything is
recorded, it waits `fallback` seconds instead, so previews work without
sound.

- A phrase is the **first few words** of the sentence the animation should
  hit. Three to five words is enough to be unique.
- Phrases are searched for **in order**, from the previous cue onward, so
  the same words can appear many times in the video.
- Capitals and punctuation don't matter.
- `offset` moves a cue later (or earlier, if negative) in seconds.
- The first scene starts at 0 and has no `start` phrase.

## Giving feedback

Phrase it in terms of what you *say*. That maps straight onto the cue map:

- "The merge should come on 'C# har støtte'." The agent changes a cue phrase.
- "The checkmarks should come one at a time as I list them." The agent adds cues.
- "The caption says X, but I say Y." The agent changes the caption.
- "Scene 4 feels static." The agent adds motion on the existing cues.
- "The highlight is on the wrong word." Plain fix.

Changing a phrase needs `sync` and a re-render. Manim caches unchanged
animations, so only what changed is rendered again.

## Changing the design, or starting a new series

**A new series:** copy the whole folder (`cp -r template ../my_series`),
delete `videos/example` if you don't need it, and change `project.toml`
(language, vocabulary for Whisper) and the design.

**A new look:** everything visual comes from `design/theme.py`. Change the
colours and fonts there, update the palette table in `design/DESIGN.md`,
and render again. The scenes stay the same as long as they use the tokens
(`ACCENT`, `PILL_FILL` …) and no hard-coded values. A dark variant is in
`design/examples/theme_dark.py`; copy it over `theme.py` to try it.

**A different language:** set `language` in `project.toml` (or per video),
write the `vocabulary` as a sentence in that language, and update
`drop_phrases` and `design/VOICE.md`.

**A different subject:** nothing in the engine is about C#. For code in
another language, set `CODE_KEYWORDS` and `CODE_COMMENT` in `theme.py`.
For subjects without code, use the other building blocks: pills, cards,
arrows, `Checklist`, overlays, or plain Manim.

## Working with Claude

The folder is set up for Claude Code (in the terminal, or the Code tab of
the Claude desktop app):

- `CLAUDE.md` loads automatically and brings in `AGENTS.md`, the agent's
  playbook for the whole process. Other agent tools can be pointed at
  `AGENTS.md` directly.
- `.claude/skills/` adds one command per phase:

  | Command               | Does                                                        |
  | --------------------- | ----------------------------------------------------------- |
  | `/design <brief>`     | Sets up or changes the design system                        |
  | `/manuscript <slug>`  | Feedback on a manuscript, or extends it in your voice       |
  | `/animate <slug>`     | Scene plan, scenes, preview and visual check                |
  | `/produce <slug>`     | After recording: transcript, cues, sync, render, assemble   |

- `.claude/settings.json` allows `./pipeline` commands without a
  permission prompt each time.

A typical session: open the folder, run `/animate generics_intro`, read the
plan and the stills, record, then `/produce generics_intro`. Next day,
start with "where are we?". The agent runs `./pipeline status` and reads
the status line in `plan.md`.

## Commands

All commands go through `./pipeline`, which uses the right Python.

| Command                                     | What it does                                                                 |
| ------------------------------------------- | ---------------------------------------------------------------------------- |
| `status [slug]`                             | One line per video: manuscript, scenes, recordings, timing, renders, next step |
| `new <slug> [--title "…"]`                  | A new video folder from `videos/_skeleton`                                    |
| `check <slug>`                              | Cue names in `scenes.py` vs `video.toml`, missing classes, recordings, stale timing |
| `preview <slug> [Scene …] [-j N]`           | Render 480p15, assemble a preview, take stills                               |
| `render <slug> [Scene …] [-q l\|m\|h\|p\|k] [-j N]` | Render scenes (default 1080p60). `-j 3` renders three at once        |
| `stills <slug> [Scene …] [-q …]`            | PNG frames before every cue + a contact sheet per scene                      |
| `transcript <slug>`                         | Transcribe (cached) and print the text with times                            |
| `sync <slug> [--fuzzy]`                     | Find the cues in the speech, write `timing.json` and per-scene clips          |
| `assemble <slug> [-q …]`                    | Join scenes and sound into `output/<slug>.mp4`, and check the lengths        |
| `build <slug>`                              | `sync`, `render -q h`, `assemble`                                            |

## Folders

```
template/
├── README.md            this guide
├── AGENTS.md            the agent's playbook
├── CLAUDE.md            Claude Code entry point (imports AGENTS.md)
├── .claude/             skills (slash commands) and permissions for Claude
├── pipeline             runs engine/pipeline.py with .venv's Python
├── setup.sh             creates .venv, checks ffmpeg and fonts
├── project.toml         series settings: language, Whisper, recording order, timing
├── design/
│   ├── DESIGN.md        visual rules: palette roles, layout, motion, captions, QA
│   ├── VOICE.md         the narrator's voice, for manuscript feedback
│   ├── theme.py         the design tokens (colours, fonts, sizes, code keywords)
│   └── examples/        alternative themes
├── engine/
│   ├── kit.py           Manim building blocks: TimedScene, Caption, CodeBlock …
│   └── pipeline.py      transcribe, sync, render, stills, assemble, check, status
├── videos/
│   ├── _skeleton/       copied by `new`
│   └── <slug>/
│       ├── manuscript.md
│       ├── plan.md      scene plan, decisions to check, status line
│       ├── video.toml   the cue map
│       ├── scenes.py    one Manim scene class per part of the manuscript
│       └── audio/       your recordings
├── build/<slug>/        generated: transcripts, timing.json, clips, renders, stills
└── output/              finished videos
```

`build/` can always be deleted; the most it costs is re-transcribing and
re-rendering.

## Troubleshooting

| Message or symptom                                     | What to do                                                                                   |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| `did not find «…»`                                     | The error shows the closest match and the speech around it. Write the phrase the way Whisper heard it, or `sync --fuzzy` |
| `[timing] Scene: «cue» 1.2 s late`                     | The animations before that cue take longer than the speech. Shorten their `run_time`        |
| `cues never waited for`                                | A cue in `video.toml` that the scene never uses. Remove it, or add `self.cue(...)`           |
| `runs N s past its audio`                              | The scene doesn't end with `finish()` / `until_end()`                                        |
| `Rendered with older timing`                           | You synced after rendering. Render those scenes again                                         |
| Transcript in Nynorsk, or odd spellings                | Write `vocabulary` as a full sentence in the written standard you want                       |
| A line you never said ("Teksting av …")                | Whisper invents subtitle credits in silence. Add the start of the line to `drop_phrases`     |
| `The font … gave N glyphs for M characters`            | The code font has ligatures. Choose another in `theme.py` (`MONO_FONTS`)                     |
| Picture and sound lengths differ after `assemble`      | A scene's ending isn't tied to its audio. Check the `[timing]` lines from the render         |
