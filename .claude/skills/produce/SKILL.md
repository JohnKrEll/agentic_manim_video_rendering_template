---
name: produce
description: After the voiceover is recorded, transcribe it, fit the cue phrases and captions to what was actually said, sync, render at 1080p60 and assemble the finished video, then verify picture/sound and the stills. Also use it to apply feedback on a finished video.
---

# Produce

Video (and any feedback to apply): $ARGUMENTS

Run **Phase 4** (or **Phase 5** for feedback) from AGENTS.md.

1. `./pipeline status <slug>` and `./pipeline check <slug>`. Make sure the
   recordings are listed in the right order.
2. `./pipeline transcript <slug>` with `run_in_background` the first time
   (Whisper on CPU takes a few minutes). Then read `build/<slug>/transcript.md`
   beside the manuscript and update `video.toml` (phrases as Whisper heard
   them), the captions in `scenes.py` that should follow the actual words,
   `drop_phrases` for invented lines, and `vocabulary` if the written
   standard is off. Note possible stumbles for the author.
3. `./pipeline sync <slug>`; fix any `did not find` from the hint it prints.
   Check that each cue in the printed table lands on the intended words.
4. `./pipeline render <slug> -j 3` with `run_in_background`. Fix every
   `[timing]` warning and render again.
5. `./pipeline assemble <slug>`: picture and sound must match.
6. `./pipeline stills <slug> -q h`, and Read every sheet.
7. Log the changes and set the Status line in `plan.md`.
8. Report: the output file, its length and size, the picture/sound
   numbers, the cues hit, the phrases and captions changed to fit the
   recording, and anything to listen for.
