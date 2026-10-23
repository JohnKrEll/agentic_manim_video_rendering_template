"""Example: the opening of the generics intro, one scene per part of manuscript.md.

A reference for how scenes are written in this template:

* every scene derives from TimedScene and waits for the narration with
  ``self.cue("name", fallback=…)``; the phrase for each cue is in video.toml
* captions go through ``Caption`` and are played *with* the picture
* code is a CodeBlock, so single tokens can be found, highlighted and morphed
* WithoutGenerics ends on exactly the frame ContainerT starts with, so the
  cut between them is invisible

Render:
    ./pipeline preview example
    ./pipeline build example
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "engine"))

from kit import *  # noqa: E402,F403

# --------------------------------------------------------------------------
# Shared pictures: built the same way where one scene ends and the next begins
# --------------------------------------------------------------------------
CODE_Y = 0.45


def list_pills():
    """«List<string>» and «List<int>» side by side."""
    ls = pill("List<string>", ACCENT_2, size=40)
    li = pill("List<int>", ACCENT_2, size=40)
    VGroup(ls, li).arrange(RIGHT, buff=1.4).move_to([0, 0.35, 0])
    return ls, li


def container_one_line():
    """Container<T> on one line, as it looks right after the merge."""
    k = CodeBlock("public class Container<T> { public T Value { get; set; } }", size=24, frame=False)
    k.move_to([0, CODE_Y, 0])
    return k, card_around(k)


def container(name="T", y=CODE_Y, size=36):
    k = CodeBlock(f"public class Container<{name}>\n{{\n    public {name} Value {{ get; set; }}\n}}", size=size)
    k.move_to([0, y, 0])
    return k


# ==========================================================================
# 1. Opening: List<string> and List<int>, but nobody wrote two list classes
# ==========================================================================
class Opening(TimedScene):
    def construct(self):
        c = Caption(self)
        ls, li = list_pills()
        self.play(
            LaggedStart(FadeIn(ls, shift=UP * 0.3), FadeIn(li, shift=UP * 0.3), lag_ratio=0.35),
            run_time=1.2,
        )

        # Two list classes? Ghost classes under each pill that never existed.
        ghosts = VGroup()
        for p, name in ((ls, "class StringList"), (li, "class IntList")):
            t = mono(name, size=26, color=MUTED)
            r = DashedVMobject(
                RoundedRectangle(corner_radius=0.14, width=t.width + 0.6, height=t.height + 0.55),
                num_dashes=40,
            ).set_stroke(FAINT, width=2)
            t.move_to(r)
            ghosts.add(VGroup(r, t).next_to(p, DOWN, buff=0.9))
        questions = VGroup(*[arrow(p.get_bottom(), g.get_top(), color=FAINT) for p, g in zip((ls, li), ghosts)])
        self.cue("ghosts", fallback=1.2)
        self.play(FadeIn(ghosts), Create(questions), c.say("To forskjellige listeklasser?"), run_time=0.9)

        # Title card
        t = Text("Generics", font=SANS, font_size=76, color=FG, weight=BOLD).move_to([0, 1.3, 0])
        sub = label("Én klasse – alle datatyper", size=32, color=MUTED).next_to(t, DOWN, buff=0.3)
        line = Line(LEFT * 1.6, RIGHT * 1.6, stroke_color=ACCENT, stroke_width=6).next_to(sub, DOWN, buff=0.35)
        self.cue("title", fallback=1.6)
        self.play(
            FadeOut(ghosts, shift=DOWN * 0.3), FadeOut(questions), c.clear(),
            VGroup(ls, li).animate.scale(0.7).shift(DOWN * 1.3),
            FadeIn(t, shift=DOWN * 0.2),
            run_time=1.0,
        )
        self.play(FadeIn(sub), Create(line), run_time=0.7)
        self.finish(fallback=2.2, run_time=0.6)


# ==========================================================================
# 2. Without generics: three identical classes, merged into one
# ==========================================================================
class WithoutGenerics(TimedScene):
    def construct(self):
        c = Caption(self)
        head = heading("Uten generics", size=38)

        sources = [
            "public class StringContainer { public string Value { get; set; } }",
            "public class IntContainer    { public int    Value { get; set; } }",
            "public class PersonContainer { public Person Value { get; set; } }",
        ]
        lines = VGroup(*[CodeBlock(s, size=22, frame=False) for s in sources])
        lines.arrange(DOWN, aligned_edge=LEFT, buff=0.42).move_to([0, CODE_Y, 0])
        card = card_around(lines, pad=(0.5, 0.45))

        self.play(FadeIn(head), FadeIn(card), run_time=0.6)
        for k in lines:
            self.play(Write(k.text), run_time=1.1)

        # The types get colour, the rest turns grey.
        types = [k.find(t)[0] for k, t in zip(lines, ("string", "int", "Person"))]
        type_marks = VGroup(*[k.highlight(g, ACCENT_2) for k, g in zip(lines, types)])
        self.cue("identical", fallback=0.6)
        self.play(
            FadeIn(type_marks),
            *[k.dim_rest(keep=[g]) for k, g in zip(lines, types)],
            c.say("Helt like, bortsett fra datatypen"),
            run_time=1.0,
        )

        # A rule that has to change, has to change in three places.
        rules = [k.find("{ get; set; }")[0] for k in lines]
        rule_marks = VGroup(*[k.highlight(g, ACCENT) for k, g in zip(lines, rules)])
        # Under the card's right corner: the card fills the width of the frame.
        times3 = pill("× 3", ACCENT, size=30).next_to(card, DOWN, buff=0.3).align_to(card, RIGHT)
        self.cue("rule", fallback=2.4)
        self.play(
            LaggedStart(*[FadeIn(m, scale=1.3) for m in rule_marks], lag_ratio=0.3),
            *[g.animate.set_opacity(1) for g in rules],
            c.say("Endrer vi en regel, må vi endre den tre steder"),
            run_time=1.2,
        )
        self.play(FadeIn(times3, shift=LEFT * 0.2), run_time=0.5)
        self.cue("smell", fallback=2.2)
        self.play(
            FadeOut(rule_marks), FadeOut(times3),
            *[g.animate.set_opacity(0.28) for g in rules],
            c.say("En umiddelbar code smell"),
            run_time=0.8,
        )

        # The merge: the three classes glide together, the types become T.
        one, one_card = container_one_line()
        t_mark = one.highlight(one.find("T")[0], ACCENT)
        t_mark_2 = one.highlight(one.find("T")[1], ACCENT)
        self.cue("merge", fallback=1.8)
        self.play(c.say("C# har støtte for generics"), run_time=0.4)
        morph_code(
            self,
            lines[0],
            one,
            extra=[
                *[k.animate.move_to(one).set_opacity(0) for k in lines[1:]],
                ReplacementTransform(type_marks[0], t_mark),
                *[ReplacementTransform(m, t_mark_2.copy()) for m in type_marks[1:]],
                ReplacementTransform(card, one_card),
                FadeIn(t_mark_2),
                head.animate.set_opacity(0.0),
            ],
            run_time=1.8,
        )
        self.remove(*lines[1:])
        self.cue("param", fallback=0.4)
        self.play(c.say("Én klasse, og typen er blitt en parameter: T"), run_time=0.9)

        # ContainerT starts with exactly this picture, without caption and marks.
        self.until_end(0.7, fallback=2.6)
        self.play(
            c.clear(),
            *[FadeOut(m) for m in self.mobjects if m not in (one, one_card, c.mobj)],
            run_time=0.7,
        )


# ==========================================================================
# 3. Container<T>: the type parameter
# ==========================================================================
class ContainerT(TimedScene):
    def construct(self):
        c = Caption(self)
        one, one_card = container_one_line()
        self.add(one_card, one)
        self.wait(0.3)

        k = container("T")
        morph_code(self, one, k, frame_from=one_card, run_time=1.3)

        # The slightly odd <T>
        brackets = k.find("<T>")[0]
        bracket_mark = k.highlight(brackets, ACCENT)
        self.cue("brackets", fallback=1.4)
        self.play(FadeIn(bracket_mark, scale=1.2), c.say("<T> er et typeparameter"), run_time=0.8)
        self.play(Indicate(brackets, color=FG, scale_factor=1.25), run_time=0.8)

        self.cue("object", fallback=2.4)
        self.play(c.say("Typen velges når vi lager et objekt"), run_time=0.7)

        # The class takes in, and gives out, data of type T.
        value = k.find("T Value")[0]
        value_mark = k.highlight(k.find("T")[1], ACCENT)
        p_in = pill("set:  tar imot T", ACCENT, size=26, fill=SOFT_FILL)
        p_out = pill("get:  gir ut T", ACCENT, size=26, fill=SOFT_FILL)
        VGroup(p_in, p_out).arrange(RIGHT, buff=1.2).next_to(k, DOWN, buff=0.9)
        a_in = arrow(p_in.get_top(), value.get_bottom() + LEFT * 0.35 + DOWN * 0.1)
        a_out = arrow(value.get_bottom() + RIGHT * 0.35 + DOWN * 0.1, p_out.get_top())
        self.cue("value", fallback=2.0)
        self.play(FadeIn(value_mark, scale=1.2), c.say("Value tar imot og gir ut data av typen T"), run_time=0.8)
        self.play(FadeIn(p_in, shift=UP * 0.2), GrowArrow(a_in), run_time=0.8)
        self.play(GrowArrow(a_out), FadeIn(p_out, shift=DOWN * 0.2), run_time=0.8)

        self.finish(fallback=3.0, run_time=0.8)
