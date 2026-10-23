"""{{TITLE}}: one scene per part of manuscript.md.

The scenes, their cues and what happens in each are planned in plan.md. The
spoken phrase for every ``self.cue(...)`` is in video.toml. videos/example/
shows the patterns: captions, code blocks, highlights, morphs, handoffs.

Render:
    ./pipeline preview {{SLUG}}
    ./pipeline build {{SLUG}}
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "engine"))

from kit import *  # noqa: E402,F403


# ==========================================================================
# 1. Opening
# ==========================================================================
class Opening(TimedScene):
    def construct(self):
        c = Caption(self)
        t = Text("{{TITLE}}", font=SANS, font_size=72, color=FG, weight=BOLD)
        line = Line(LEFT * 1.6, RIGHT * 1.6, stroke_color=ACCENT, stroke_width=6).next_to(t, DOWN, buff=0.4)
        self.cue("title", fallback=1.0)
        self.play(FadeIn(t, shift=DOWN * 0.2), Create(line), c.say("…"), run_time=1.0)
        self.finish(fallback=2.0)
