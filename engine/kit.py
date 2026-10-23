"""Building blocks for the scenes: timing against the voiceover, captions,
code blocks you can address token by token, pills, cards, arrows and marks.

Every visual token (colours, fonts, sizes, code keywords) comes from
design/theme.py, so the same scenes can be re-skinned by changing that file.
The rules for using them are in design/DESIGN.md.

A scene file imports everything with::

    from kit import *

which also brings in Manim and the theme tokens (BG, FG, ACCENT, ...).

No LaTeX is used anywhere (all text is Text/Pango), so scenes render without
a TeX installation.
"""

import difflib
import inspect
import json
import pathlib
import re
import sys
from statistics import median

from manim import *

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"

sys.path.insert(0, str(ROOT / "design"))
from theme import *  # noqa: E402,F403

config.background_color = BG


# --------------------------------------------------------------------------
# Timing against the voiceover
# --------------------------------------------------------------------------
class TimedScene(Scene):
    """A scene that can be timed against the voiceover.

    The video is the folder the scene file lives in (videos/<slug>/scenes.py).
    When ``build/<slug>/timing.json`` has an entry for the scene, the scene's
    audio clip is added from the start, and ``cue("name")`` waits until the
    moment in the clip where that cue's phrase is spoken. Without timing,
    ``cue`` is a plain ``wait(fallback)``, so scenes can still be rendered and
    previewed before anything is recorded.

    Each scene has its own audio clip, so a scene that runs slightly long
    never shifts the audio in the other scenes.
    """

    def setup(self):
        self._slug = pathlib.Path(inspect.getfile(type(self))).resolve().parent.name
        self._timing = {}
        self._used = set()
        fil = BUILD / self._slug / "timing.json"
        if fil.exists():
            self._timing = json.loads(fil.read_text()).get(type(self).__name__, {})
        if self._timing:
            self.add_sound(str(BUILD / self._slug / "clips" / f"{type(self).__name__}.wav"))

    @property
    def timed(self):
        return bool(self._timing)

    def cue(self, name, fallback=0.0):
        """Wait until cue ``name`` is spoken. Without timing: wait ``fallback`` s."""
        if not self._timing:
            if fallback > 0:
                self.wait(fallback)
            return
        cues = self._timing["cues"]
        if name not in cues:
            raise KeyError(
                f"{type(self).__name__}: cue {name!r} is not in video.toml "
                f"(known: {', '.join(cues) or 'none'}). Add it and run sync again."
            )
        self._used.add(name)
        self._wait_until(cues[name], name)

    def _wait_until(self, t, name):
        rest = t - self.renderer.time
        if rest > 1 / 60:
            self.wait(rest)
        elif rest < -0.25:
            # The animations before this cue take longer than the speech allows.
            print(f"[timing] {type(self).__name__}: «{name}» {-rest:.1f} s late", flush=True)

    def until_end(self, run_time, fallback=2.0):
        """Wait until only ``run_time`` seconds of the audio clip are left."""
        if self._timing:
            self._wait_until(self._timing["length"] - run_time, "end")
        elif fallback > 0:
            self.wait(fallback)

    def finish(self, fallback=2.0, run_time=0.9):
        """Fade everything out, so the scene ends when its audio clip ends."""
        self.until_end(run_time, fallback)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=run_time)

    def tear_down(self):
        if not self._timing:
            return
        unused = [c for c in self._timing["cues"] if c not in self._used]
        if unused:
            print(f"[timing] {type(self).__name__}: cues never waited for: {', '.join(unused)}", flush=True)
        over = self.renderer.time - self._timing["length"]
        if over > 0.1:
            print(f"[timing] {type(self).__name__}: runs {over:.1f} s past its audio", flush=True)


# --------------------------------------------------------------------------
# Fonts: the first one that is installed on the rendering machine.
# --------------------------------------------------------------------------
def _pick_font(candidates, default=""):
    try:
        from manimpango import list_fonts

        installed = set(list_fonts())
    except Exception:  # pragma: no cover - depends on the system
        return default
    for c in candidates:
        if c in installed:
            return c
    return default


SANS = _pick_font(SANS_FONTS)
MONO = _pick_font(MONO_FONTS, "monospace")


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------
def label(t, size=TEXT_SIZE, color=FG, **kwargs):
    """Body text in the sans font."""
    kwargs.setdefault("font", SANS)
    return Text(t, font_size=size, color=color, **kwargs)


def mono(t, size=CODE_SIZE - 4, color=FG, **kwargs):
    """A short piece of text in the code font (not addressable; see CodeBlock)."""
    return Text(t, font=MONO, font_size=size, color=color, **kwargs)


def heading(t, subtitle=None, size=HEADING_SIZE):
    """A heading (with optional subtitle) anchored to the top of the frame.

    Use it for title cards. A heading that stays up for a whole scene eats
    the space the content needs (see DESIGN.md).
    """
    main = Text(t, font=SANS, font_size=size, color=FG, weight=BOLD)
    group = VGroup(main)
    if subtitle:
        s = Text(subtitle, font=SANS, font_size=size * 0.52, color=MUTED)
        s.next_to(main, DOWN, buff=0.22)
        group.add(s)
    group.to_edge(UP, buff=0.5)
    return group


class Caption:
    """The fixed explanation line at the bottom of the frame.

    ``say()`` returns an animation, so it can be played together with what
    happens in the picture::

        c = Caption(self)
        self.play(c.say("First explanation"), FadeIn(thing))
    """

    def __init__(self, scene, y=-3.45, size=CAPTION_SIZE, max_width=12.5):
        self.y = y
        self.size = size
        self.max_width = max_width
        self.mobj = self._make("", MUTED)
        self._visible = False
        # Foreground: the caption is always drawn last, and changing it does
        # not drag the rest of the picture into the "moving" layer (where
        # z-index is sorted separately, and a filled code card could cover
        # the highlights).
        scene.add_foreground_mobject(self.mobj)

    def _make(self, t, color):
        new = label(t, size=self.size, color=color)
        if new.width > self.max_width:
            new.scale_to_fit_width(self.max_width)
        return new.move_to([0, self.y, 0])

    def say(self, t, color=MUTED):
        new = self._make(t, color)
        if not self._visible:
            # From an empty line: start as an invisible copy in place and fade
            # in. (A Transform from empty text grows out of the frame centre.)
            self.mobj.become(new.copy().set_opacity(0))
        self._visible = True
        return Transform(self.mobj, new)

    def clear(self):
        self._visible = False
        return self.mobj.animate.set_opacity(0)


# --------------------------------------------------------------------------
# Pills, cards, arrows and marks
# --------------------------------------------------------------------------
def pill(t, color=ACCENT_2, size=34, pad=0.28, monospace=True, fill=PILL_FILL):
    """Dark text on a rounded accent-coloured surface: «List<string>» etc.

    The height is fixed per font size, so pills in a row line up even when
    only some of them have letters with descenders (g, p, y ...).
    """
    make = mono if monospace else label
    txt = make(t, size=size, color=ON_ACCENT)
    ref = make("Ag", size=size)
    r = RoundedRectangle(
        corner_radius=0.14,
        width=txt.width + 2 * pad,
        height=ref.height + 1.3 * pad,
        stroke_color=color,
        stroke_width=2,
        fill_color=color,
        fill_opacity=fill,
    )
    txt.move_to(r)
    return VGroup(r, txt)


def card_around(mobj, pad=(0.45, 0.35), color=CARD, stroke=CARD_STROKE):
    """A code-card background around any mobject."""
    r = RoundedRectangle(
        corner_radius=0.16,
        width=mobj.width + 2 * pad[0],
        height=mobj.height + 2 * pad[1],
        fill_color=color,
        fill_opacity=1,
        stroke_color=stroke,
        stroke_width=1.6,
    ).move_to(mobj)
    r.set_z_index(-2)
    return r


def arrow(start, end, color=FG, buff=0.12, width=3.0):
    return Arrow(
        start,
        end,
        buff=buff,
        stroke_width=width,
        max_tip_length_to_length_ratio=0.18,
        color=color,
    )


def pulse(m, scale=1.08, run_time=0.8):
    """A short "breath" that points at something without recolouring it."""
    return Succession(
        m.animate(rate_func=rate_functions.ease_out_sine).scale(scale),
        m.animate(rate_func=rate_functions.ease_in_sine).scale(1 / scale),
        run_time=run_time,
    )


def squiggle(mobj, color=ERROR, wave=0.11, amp=0.045, gap=0.09):
    """The compiler's "squiggly line" under a piece of code."""
    x0, x1 = mobj.get_left()[0], mobj.get_right()[0]
    y = mobj.get_bottom()[1] - gap
    n = max(2, int((x1 - x0) / (wave / 2)))
    pts = [[x0 + (x1 - x0) * i / n, y + (amp if i % 2 else -amp), 0] for i in range(n + 1)]
    return VMobject().set_points_as_corners(pts).set_stroke(color, width=3.5)


def status(ok, radius=0.22):
    """The result of one check: ✓ on the OK colour or ✗ on the ERROR colour."""
    c = Circle(radius=radius).set_fill(OK if ok else ERROR, 1).set_stroke(FG, 2)
    t = label("✓" if ok else "✗", size=int(radius * 110), color=ON_ACCENT, weight=BOLD).move_to(c)
    return VGroup(c, t)


def empty_status(radius=0.22):
    """An empty slot where a ✓/✗ will appear."""
    return Circle(radius=radius).set_stroke(FAINT, 2).set_fill(opacity=0)


def overlay(content, pad=(0.6, 0.5), z=5):
    """A card that lies on top of the picture (the «T = ?» window)."""
    surface = RoundedRectangle(
        corner_radius=0.2,
        width=content.width + 2 * pad[0],
        height=content.height + 2 * pad[1],
        fill_color=CARD,
        fill_opacity=1,
        stroke_color=FG,
        stroke_width=2,
    ).move_to(content)
    g = VGroup(surface, content)
    surface.set_z_index(z)
    for m in content.get_family():
        m.set_z_index(z + 1)
    return g


class Checklist(VGroup):
    """A card with a heading and rows, each with a slot for ✓/✗ on the right.

    The testing video used one checklist as its recurring figure: the car
    report, the inspection, the test run and the summary.
    """

    def __init__(self, title, items, width=6.4, monospace=False, size=28, row_gap=0.62):
        super().__init__()
        self.monospace = monospace
        self.size = size
        self.head = label(title, size=size + 4, weight=BOLD)
        self.labels = VGroup(*[self._label(p) for p in items])
        for i, e in enumerate(self.labels):
            e.move_to([0, -i * row_gap, 0], aligned_edge=LEFT)
        self.head.next_to(self.labels, UP, buff=0.5, aligned_edge=LEFT)
        content = VGroup(self.head, self.labels)
        self.frame = RoundedRectangle(
            corner_radius=0.18, width=width, height=content.height + 0.9,
            fill_color=CARD, fill_opacity=1, stroke_color=CARD_STROKE, stroke_width=1.8,
        )
        self.frame.move_to(content).align_to(content, LEFT).shift(LEFT * 0.45)
        self.slots = VGroup(
            *[empty_status().move_to([self.frame.get_right()[0] - 0.55, e.get_y(), 0]) for e in self.labels]
        )
        self.marks = [None] * len(items)
        self.add(self.frame, self.head, self.labels, self.slots)

    def _label(self, t):
        return (mono if self.monospace else label)(t, size=self.size)

    def mark(self, i, ok):
        """Animation: show the result on row ``i``."""
        m = status(ok).move_to(self.slots[i])
        old = self.marks[i]
        self.marks[i] = m
        self.add(m)
        if old is None:
            return FadeIn(m, scale=1.4)
        self.remove(old)
        return ReplacementTransform(old, m)

    def reset(self):
        """Animation: remove all results, ready for a new run."""
        old = [m for m in self.marks if m is not None]
        self.remove(*old)
        self.marks = [None] * len(self.marks)
        return AnimationGroup(*[FadeOut(m) for m in old])

    def relabel(self, items, monospace=None):
        """Animation: new texts on the rows (car parts → test names)."""
        if monospace is not None:
            self.monospace = monospace
        anims = []
        for e, p in zip(self.labels, items):
            new = self._label(p).move_to(e, aligned_edge=LEFT)
            anims.append(Transform(e, new))
        return AnimationGroup(*anims)


# --------------------------------------------------------------------------
# Code: a code block where every token can be looked up, marked and animated
# --------------------------------------------------------------------------
_TOKEN = re.compile(r"\w+|[^\w\s]")
_NO_DESCENDER = set("ABCDEFGHIKLMNOPRSTUVWXZabcdefhiklmnorstuvwxz0123456789")
_CAPITAL = set("ABCDEFGHIKLMNOPRSTUVWXZ0123456789")


class CodeBlock(VGroup):
    """Source code as one Text object, with a map from source text to glyphs.

    ``Text`` makes one glyph per non-whitespace character, in reading order,
    so we can work out which glyph draws a given position in the source. That
    gives us:

    * ``find("T")``          the glyphs for each occurrence of a word/symbol
    * ``highlight(...)``     a coloured surface behind one occurrence
    * ``morph_code(...)``    animate one code block into another, token by token

    (Named CodeBlock because Manim already has a ``Code`` class.)
    """

    def __init__(
        self,
        source,
        size=CODE_SIZE,
        frame=True,
        pad=(0.5, 0.38),
        max_width=12.6,
        line_spacing=1.0,
        keywords=CODE_KEYWORDS,
        comment=CODE_COMMENT,
    ):
        super().__init__()
        self.source = source
        self.text = mono(source, size=size, line_spacing=line_spacing)

        count = sum(1 for c in source if not c.isspace())
        if count != len(self.text):
            raise ValueError(
                f"The font {MONO!r} gave {len(self.text)} glyphs for {count} characters "
                "(ligatures?). Pick a code font without ligatures in design/theme.py."
            )

        self._glyph_at = {}  # position in the source -> glyph index
        self._line_of = {}  # id(glyph) -> line number
        self._char_of = {}  # id(glyph) -> the character it draws
        self._lines = [[] for _ in source.split("\n")]
        g = line = 0
        for i, c in enumerate(source):
            if c == "\n":
                line += 1
            elif not c.isspace():
                glyph = self.text[g]
                self._glyph_at[i] = g
                self._line_of[id(glyph)] = line
                self._char_of[id(glyph)] = c
                self._lines[line].append(glyph)
                g += 1

        # Muted syntax colouring: the accents are reserved for the concept.
        if keywords:
            for m in re.finditer(r"\b(%s)\b" % "|".join(keywords), source):
                self._glyphs(m.start(), m.end()).set_color(MUTED)
        if comment:
            for m in re.finditer(comment, source):
                self._glyphs(m.start(), m.end()).set_color(FAINT)

        self.add(self.text)
        self.frame = None
        if frame:
            self.frame = card_around(self.text, pad=pad)
            self.add_to_back(self.frame)
        if self.width > max_width:
            self.scale_to_fit_width(max_width)

    # -- lookup -----------------------------------------------------------
    def _glyphs(self, start, end):
        return VGroup(*[self.text[self._glyph_at[i]] for i in range(start, end) if i in self._glyph_at])

    def find(self, pattern):
        """The glyphs for each occurrence of ``pattern``, as whole words."""
        rx = re.escape(pattern)
        if re.match(r"\w", pattern[0]):
            rx = r"(?<!\w)" + rx
        if re.match(r"\w", pattern[-1]):
            rx = rx + r"(?!\w)"
        found = [self._glyphs(m.start(), m.end()) for m in re.finditer(rx, self.source)]
        if not found:
            raise ValueError(f"{pattern!r} does not occur in the code block")
        return found

    def line(self, i):
        return VGroup(*self._lines[i])

    # -- geometry ---------------------------------------------------------
    def _cap_height(self):
        heights = [g.height for g in self.text if self._char_of[id(g)] in _CAPITAL]
        if not heights:
            heights = [g.height for g in self.text if self._char_of[id(g)] in "bdfhklt"]
        return median(heights) if heights else self.text.height / len(self._lines) * 0.6

    def _baseline(self, i):
        """The y value of the baseline of line ``i``.

        Glyph boxes vary (g and p hang below, { and } are tall), so we use the
        bottom of letters without descenders, and fall back to the line
        spacing for lines that only contain characters like { and }.
        """

        def measured(n):
            b = [g.get_bottom()[1] for g in self._lines[n] if self._char_of[id(g)] in _NO_DESCENDER]
            return median(b) if b else None

        y = measured(i)
        if y is not None:
            return y
        known = [(n, measured(n)) for n in range(len(self._lines))]
        known = [(n, v) for n, v in known if v is not None]
        if len(known) >= 2:
            (n0, y0), (n1, y1) = known[0], known[-1]
            step = (y0 - y1) / (n1 - n0)
            n, v = min(known, key=lambda k: abs(k[0] - i))
            return v - (i - n) * step
        return self.line(i).get_bottom()[1]

    def _surface(self, x0, x1, line, color, opacity, radius=0.07):
        cap = self._cap_height()
        bl = self._baseline(line)
        top, bottom = bl + cap * 1.32, bl - cap * 0.45
        r = RoundedRectangle(
            corner_radius=radius,
            width=x1 - x0,
            height=top - bottom,
            stroke_width=0,
            fill_color=color,
            fill_opacity=opacity,
        ).move_to([(x0 + x1) / 2, (top + bottom) / 2, 0])
        r.set_z_index(-1)
        return r

    def highlight(self, glyphs, color=ACCENT, opacity=HIGHLIGHT_OPACITY, pad=0.07):
        """A coloured surface behind one occurrence (glyphs from ``find``)."""
        line = self._line_of[id(glyphs[0])]
        return self._surface(glyphs.get_left()[0] - pad, glyphs.get_right()[0] + pad, line, color, opacity)

    def highlights(self, pattern, color=ACCENT, opacity=HIGHLIGHT_OPACITY):
        """Surfaces behind *every* occurrence of ``pattern``."""
        return VGroup(*[self.highlight(g, color, opacity) for g in self.find(pattern)])

    def line_highlight(self, i, color=ACCENT, opacity=0.3):
        """A surface behind a whole line: the card's inner width if it has one."""
        if self.frame is not None:
            x0, x1 = self.frame.get_left()[0] + 0.12, self.frame.get_right()[0] - 0.12
        else:
            x0, x1 = self.line(i).get_left()[0] - 0.1, self.line(i).get_right()[0] + 0.1
        return self._surface(x0, x1, i, color, opacity, radius=0.05)

    def dim_rest(self, keep=(), f=0.28):
        """Animation: fade every glyph that is not in ``keep`` down to ``f``.

        (Not called ``dim``: Manim uses ``Mobject.dim`` for the number of dimensions.)
        """
        spare = {id(m) for group in keep for m in group}
        return AnimationGroup(*[g.animate.set_opacity(f) for g in self.text if id(g) not in spare])

    def tokens(self):
        """(token, first glyph, glyph after the last) in source order."""
        out = []
        for m in _TOKEN.finditer(self.source):
            start = self._glyph_at[m.start()]
            out.append((m.group(), start, start + len(m.group())))
        return out


def morph_code(scene, a, b, extra=(), frame_from=None, run_time=1.6, **kwargs):
    """Animate code block ``a`` into ``b``, token by token.

    Tokens that are in both glide to their new place, tokens that were
    replaced transform, and the rest fade in or out. Afterwards ``b`` is in
    the scene as one whole object, ready to be used further.

    ``frame_from`` lets a separate card glide into ``b``'s frame.
    """
    ta, tb = a.tokens(), b.tokens()
    ops = difflib.SequenceMatcher(None, [t[0] for t in ta], [t[0] for t in tb], autojunk=False).get_opcodes()

    def glyphs(k, toks):
        return VGroup(*[k.text[g] for _, s, e in toks for g in range(s, e)])

    anims, temporary = [], []
    for op, i1, i2, j1, j2 in ops:
        ga, gb = glyphs(a, ta[i1:i2]), glyphs(b, tb[j1:j2])
        if op == "equal":
            anims += [ReplacementTransform(x, y) for x, y in zip(ga, gb)]
        elif op == "replace":
            anims.append(ReplacementTransform(ga, gb))
        elif op == "delete":
            anims.append(FadeOut(ga))
        else:
            anims.append(FadeIn(gb))
        temporary += [ga, gb]

    src = frame_from if frame_from is not None else a.frame
    if src is not None and b.frame is not None:
        anims.append(ReplacementTransform(src, b.frame))
    elif src is not None:
        anims.append(FadeOut(src))
        temporary.append(src)
    elif b.frame is not None:
        anims.append(FadeIn(b.frame))

    scene.play(*anims, *extra, run_time=run_time, **kwargs)

    # Clean up: replace all the pieces with b as one object.
    remove = set()
    for m in [a, b, *temporary]:
        remove |= {id(x) for x in m.get_family()}
    scene.mobjects = [m for m in scene.mobjects if id(m) not in remove]
    scene.add(b)
