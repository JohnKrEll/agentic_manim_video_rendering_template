# Claude Code: Manim video template

@AGENTS.md

## Claude-specific notes

- **Look at the stills.** Use Read on `build/<slug>/stills/<Scene>_sheet.png`
  (one contact sheet per scene) after every preview and final render. You can
  see images; a render with no errors can still have clipped or overlapping
  elements. Open single frames beside the sheet when you need detail.
- **Background jobs.** Run `./pipeline transcript`, `sync` (when it has to
  transcribe), `render -q h` and `build` with `run_in_background`. You are
  notified when they finish, so don't poll. Previews (`preview`) usually take
  under a minute and can run in the foreground.
- **Phase commands.** `.claude/skills/` has `/design`, `/manuscript`,
  `/animate` and `/produce`, one per phase in AGENTS.md. Follow the phase
  even when the user asks in plain words instead of using a command.
- **What to remember where.** Write durable learnings into the project, not
  only into your memory: voice corrections go in `design/VOICE.md`, visual
  rules in `design/DESIGN.md`, and per-video state in `videos/<slug>/plan.md`.
  These travel with the template when it is copied.
- **Subagents.** One agent should own a video's `scenes.py`. For a long
  video it is fine to have a subagent draft a scene, but integrate and
  check it yourself (`./pipeline check`, preview, stills).
- **Permissions.** `.claude/settings.json` allows `./pipeline …` commands.
  Anything else (pip installs, deleting recordings) still asks.
- Use the pipeline instead of calling `manim` or `ffmpeg` directly; it keeps
  media, timing and render records in the places the other commands expect.
