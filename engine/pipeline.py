"""The video pipeline: from manuscript and recordings to a finished .mp4.

Run it through the wrapper in the project root, which picks the right Python:

    ./pipeline status                        where every video is in the process
    ./pipeline new <slug> [--title "..."]    a new video folder from videos/_skeleton
    ./pipeline check <slug>                  video.toml vs scenes.py, manuscript and recordings
    ./pipeline preview <slug> [Scene ...]    quick render (480p15) + stills (+ preview .mp4)
    ./pipeline render <slug> [Scene ...]     render the scenes (-q l|m|h|p|k, default h)
    ./pipeline stills <slug> [Scene ...]     PNG frames at every cue, for checking the layout
    ./pipeline transcript <slug>             transcribe the recordings (cached) and show the text
    ./pipeline sync <slug> [--fuzzy]         timing.json + one audio clip per scene
    ./pipeline assemble <slug>               join scenes + voice into output/<slug>.mp4
    ./pipeline build <slug>                  sync -> render -q h -> assemble

How the sync works:
1. Every recording in videos/<slug>/audio/ is transcribed with Whisper, with
   a timestamp per word (cached in build/<slug>/transcripts/, keyed on the
   file's contents, so a re-take is transcribed again and nothing else is).
2. The recordings are joined in order, with the silence at their ends trimmed.
3. Each scene's start phrase and cue phrases (video.toml) are searched for in
   that order in the joined text, so the same words can be used many times.
4. The voice is cut into one clip per scene (build/<slug>/clips/), and the
   cue times relative to each scene go into build/<slug>/timing.json, which
   TimedScene in kit.py reads at render time.
"""

import argparse
import ast
import difflib
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parents[1]
VIDEOS = ROOT / "videos"
BUILD = ROOT / "build"
OUTPUT = ROOT / "output"
ENGINE = ROOT / "engine"

QUALITY = {
    "l": ("-ql", "480p15"),
    "m": ("-qm", "720p30"),
    "h": ("-qh", "1080p60"),
    "p": ("-qp", "1440p60"),
    "k": ("-qk", "2160p60"),
}
AUDIO_TYPES = {".wav", ".flac", ".mp3", ".m4a", ".ogg", ".opus", ".aac"}
MARKER = re.compile(r"^\s*\*\[(?:Animasjon|Animation)\s*:", re.MULTILINE | re.IGNORECASE)

DEFAULTS = {
    "language": "no",
    "whisper_model": "large-v3",
    "whisper_device": "cpu",
    "whisper_compute_type": "int8",
    "vocabulary": "",
    "recordings": "name",
    "drop_phrases": [],
    "timing": {
        "cue_lead": 0.15,  # a cue fires slightly before the word, so the animation is moving when it is said
        "scene_lead": 0.3,  # a scene starts slightly before its first word
        "head": 0.25,  # silence kept before the first word of each recording
        "tail": 0.5,  # silence kept after the last word of each recording
        "fps": 60,  # scene boundaries land on whole frames, so rounding never piles up
    },
}


def die(msg):
    sys.stdout.flush()
    print(f"\n✗ {msg}", file=sys.stderr)
    sys.exit(1)


# --------------------------------------------------------------------------
# Configuration: project.toml (series-wide) + videos/<slug>/video.toml
# --------------------------------------------------------------------------
@dataclass
class SceneSpec:
    name: str
    start: str | None
    cues: dict  # name -> (phrase, offset)


@dataclass
class Video:
    slug: str
    cfg: dict
    title: str
    scenes: list = field(default_factory=list)

    folder = property(lambda self: VIDEOS / self.slug)
    build = property(lambda self: BUILD / self.slug)
    audio = property(lambda self: self.folder / "audio")
    scenes_file = property(lambda self: self.folder / "scenes.py")
    manuscript = property(lambda self: self.folder / "manuscript.md")
    timing_file = property(lambda self: self.build / "timing.json")
    clips = property(lambda self: self.build / "clips")
    transcripts = property(lambda self: self.build / "transcripts")
    media = property(lambda self: self.build / "media")
    scene_names = property(lambda self: [s.name for s in self.scenes])

    def rendered(self, q):
        return self.media / "videos" / "scenes" / QUALITY[q][1]

    def output(self, q):
        return OUTPUT / (f"{self.slug}.mp4" if q == "h" else f"{self.slug}_{QUALITY[q][1]}.mp4")

    def timing(self):
        return json.loads(self.timing_file.read_text()) if self.timing_file.exists() else {}


def _read_toml(path):
    try:
        return tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        die(f"{path.relative_to(ROOT)}: {e}")


def all_slugs():
    return sorted(p.name for p in VIDEOS.iterdir() if p.is_dir() and not p.name.startswith("_"))


def load(slug):
    if not (VIDEOS / slug / "video.toml").exists():
        die(f"No video {slug!r}. Videos: {', '.join(all_slugs()) or 'none'} (./pipeline new <slug>)")
    project = _read_toml(ROOT / "project.toml") if (ROOT / "project.toml").exists() else {}
    video = _read_toml(VIDEOS / slug / "video.toml")

    cfg = {k: v for k, v in DEFAULTS.items() if k != "timing"}
    cfg["timing"] = dict(DEFAULTS["timing"])
    for layer in (project, video):
        for k, v in layer.items():
            if k == "timing":
                cfg["timing"].update(v)
            elif k not in ("scenes", "title"):
                cfg[k] = v
    # The vocabulary adds up: the series' words, then the video's own.
    cfg["vocabulary"] = " ".join(x for x in (project.get("vocabulary", ""), video.get("vocabulary", "")) if x).strip()

    scenes = []
    for i, s in enumerate(video.get("scenes", [])):
        if "name" not in s:
            die(f"videos/{slug}/video.toml: scene {i + 1} has no name")
        cues = {}
        for name, v in s.get("cues", {}).items():
            if isinstance(v, str):
                cues[name] = (v, 0.0)
            else:
                cues[name] = (v.get("phrase", ""), float(v.get("offset", 0.0)))
        scenes.append(SceneSpec(s["name"], s.get("start") or None, cues))
    return Video(slug, cfg, video.get("title", slug), scenes)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def sh(*args):
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    if r.returncode != 0:
        die(f"{args[0]} failed:\n{r.stderr.strip()[-2000:]}")
    return r.stdout


def duration(path):
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path))


def video_length(path):
    """Length of the picture itself (the container can carry a longer audio track)."""
    out = sh("ffprobe", "-v", "error", "-select_streams", "v", "-count_packets",
             "-show_entries", "stream=nb_read_packets,r_frame_rate", "-of", "csv=p=0", path)
    rate, count = out.strip().split(",")
    num, den = rate.split("/")
    return int(count) * int(den) / int(num)


def audio_length(path):
    out = sh("ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=duration",
             "-of", "csv=p=0", path).strip()
    return float(out) if out and out != "N/A" else duration(path)


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalise(word):
    return re.sub(r"[^\w]", "", word.lower())


def rel(path):
    try:
        return str(pathlib.Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


def clock(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def manuscript_text(v):
    """The manuscript without <!-- comments -->, which are notes and never read aloud."""
    text = v.manuscript.read_text() if v.manuscript.exists() else ""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


# --------------------------------------------------------------------------
# Recordings and transcription
# --------------------------------------------------------------------------
def recordings(v, strict=True):
    """The recordings in the order they are joined. ``strict=False`` skips missing ones."""
    order = v.cfg["recordings"]
    if isinstance(order, list):
        files = [v.audio / n for n in order]
        missing = [f.name for f in files if not f.exists()]
        if missing and strict:
            die(f"Missing recordings in {rel(v.audio)}: {', '.join(missing)}")
        return [f for f in files if f.exists()]
    if not v.audio.exists():
        return []
    files = [f for f in v.audio.iterdir() if f.suffix.lower() in AUDIO_TYPES]
    if order == "recorded":
        return sorted(files, key=lambda f: f.stat().st_mtime)
    if order != "name":
        die(f'recordings = {order!r}: use "name", "recorded" or a list of file names')
    return sorted(files, key=lambda f: f.name.lower())


def _cache(v, f):
    return v.transcripts / f"{f.stem}.json"


def _whisper_settings(v):
    """What a transcript depends on besides the audio: change one, and it is redone."""
    return {k: v.cfg[k] for k in ("whisper_model", "language", "vocabulary")}


def is_transcribed(v, f):
    c = _cache(v, f)
    if not c.exists():
        return False
    data = json.loads(c.read_text())
    return data.get("sha1") == sha1(f) and data.get("settings") == _whisper_settings(v)


def transcribe(v, files):
    todo = [f for f in files if not is_transcribed(v, f)]
    if not todo:
        return
    from faster_whisper import WhisperModel

    v.transcripts.mkdir(parents=True, exist_ok=True)
    print(f"Loading Whisper {v.cfg['whisper_model']} …", flush=True)
    model = WhisperModel(
        v.cfg["whisper_model"],
        device=v.cfg["whisper_device"],
        compute_type=v.cfg["whisper_compute_type"],
        cpu_threads=os.cpu_count() or 4,
    )
    for f in todo:
        print(f"Transcribing {f.name} …", flush=True)
        t0 = time.time()
        segments, _ = model.transcribe(
            str(f),
            language=v.cfg["language"],
            word_timestamps=True,
            initial_prompt=v.cfg["vocabulary"] or None,
            beam_size=5,
        )
        data = [
            {
                "start": s.start,
                "end": s.end,
                "text": s.text.strip(),
                "words": [{"word": w.word, "start": w.start, "end": w.end} for w in s.words],
            }
            for s in segments
        ]
        cache = {"file": f.name, "sha1": sha1(f), "settings": _whisper_settings(v), "segments": data}
        _cache(v, f).write_text(json.dumps(cache, ensure_ascii=False, indent=1))
        print(f"  done in {time.time() - t0:.0f} s", flush=True)


def segments(v, f, report=True):
    """The transcribed segments of ``f``, without Whisper's known artefacts."""
    keep = []
    for s in json.loads(_cache(v, f).read_text())["segments"]:
        if any(s["text"].lower().startswith(p.lower()) for p in v.cfg["drop_phrases"]):
            if report:
                print(f"  dropped Whisper artefact in {f.name} at {s['start']:.1f} s: «{s['text']}»")
            continue
        keep.append(s)
    return keep


def cmd_transcript(v, args):
    files = recordings(v)
    if not files:
        die(f"No recordings in {rel(v.audio)}")
    transcribe(v, files)
    lines = [f"# Transcript: {v.title}", ""]
    for f in files:
        lines += [f"## {f.name}", ""]
        for s in segments(v, f, report=False):
            lines.append(f"[{s['start']:6.2f}–{s['end']:6.2f}] {s['text']}")
        dropped = len(json.loads(_cache(v, f).read_text())["segments"]) - len(segments(v, f, report=False))
        if dropped:
            lines.append(f"({dropped} segment(s) dropped by drop_phrases)")
        lines.append("")
    text = "\n".join(lines)
    v.build.mkdir(parents=True, exist_ok=True)
    (v.build / "transcript.md").write_text(text)
    print(text)
    print(f"Saved to {rel(v.build / 'transcript.md')}")


# --------------------------------------------------------------------------
# Sync: find the cues in the speech, cut one clip per scene
# --------------------------------------------------------------------------
def find(words, phrase, start, fuzzy, where):
    """Index of the first word of ``phrase``, searched from index ``start``."""
    target = [w for w in (normalise(x) for x in phrase.split()) if w]
    if not target:
        die(f"{where}: empty phrase")
    n = len(target)
    for i in range(start, len(words) - n + 1):
        if all(words[i + j]["n"] == target[j] for j in range(n)):
            return i

    # Not found: the closest stretch of the same length a little further on.
    goal = " ".join(target)
    best, best_i = 0.0, None
    for i in range(start, min(len(words) - n + 1, start + 500)):
        r = difflib.SequenceMatcher(None, goal, " ".join(w["n"] for w in words[i : i + n])).ratio()
        if r > best:
            best, best_i = r, i
    heard = " ".join(w["word"].strip() for w in words[best_i : best_i + n]) if best_i is not None else ""
    if fuzzy and best >= 0.75:
        print(f"  ~ {where}: «{phrase}» matched «{heard}» ({best:.0%}); consider writing it that way")
        return best_i
    here = words[start]["t"] if start < len(words) else 0.0
    context = " ".join(w["word"].strip() for w in words[start : start + 40])
    hint = f"\n  Closest: «{heard}» ({best:.0%}) at {words[best_i]['t']:.1f} s." if best_i is not None else ""
    die(
        f"{where}: did not find «{phrase}» after {here:.1f} s.{hint}\n"
        "  Write the phrase the way Whisper heard it (./pipeline transcript), or run sync --fuzzy.\n"
        f"  The speech from there: {context} …"
    )


def cmd_sync(v, args):
    files = recordings(v)
    if not files:
        die(f"No recordings in {rel(v.audio)}")
    if not v.scenes:
        die("video.toml has no scenes")
    print("Recordings, in order:")
    for f in files:
        print(f"  {f.name}")
    transcribe(v, files)
    t = v.cfg["timing"]

    # Join the recordings, with the silence at their ends trimmed.
    tmp = v.build / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    words, pieces, offset = [], [], 0.0
    for i, f in enumerate(files):
        spoken = [w for s in segments(v, f) for w in s["words"]]
        if not spoken:
            die(f"No speech found in {f.name}")
        length = duration(f)
        a = max(0.0, spoken[0]["start"] - t["head"])
        b = min(length, spoken[-1]["end"] + t["tail"])
        piece = tmp / f"piece{i}.wav"
        sh("ffmpeg", "-y", "-v", "error", "-i", f, "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-ar", "48000", "-ac", "2", piece)
        pieces.append(piece)
        for w in spoken:
            words.append({"n": normalise(w["word"]), "word": w["word"], "t": offset + w["start"] - a})
        offset += b - a
    words = [w for w in words if w["n"]]

    listing = tmp / "pieces.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in pieces))
    voice = v.build / "voice.wav"
    sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", voice)
    shutil.rmtree(tmp)
    total = duration(voice)

    # Scene boundaries and cues, in order.
    pos, starts, found = 0, [], []
    for i, sc in enumerate(v.scenes):
        if i == 0:
            starts.append(0.0)
        else:
            if not sc.start:
                die(f"Scene {sc.name} needs a start phrase in video.toml (only the first scene may omit it)")
            pos = find(words, sc.start, pos, args.fuzzy, f"{sc.name} (start)")
            starts.append(max(0.0, words[pos]["t"] - t["scene_lead"]))
        c = {}
        for name, (phrase, off) in sc.cues.items():
            pos = find(words, phrase, pos, args.fuzzy, f"{sc.name}, cue {name}")
            heard = " ".join(w["word"].strip() for w in words[pos : pos + 6])
            c[name] = (words[pos]["t"] - t["cue_lead"] + off, heard)
        found.append(c)
    fps = t["fps"]
    starts = [round(a * fps) / fps for a in starts]
    ends = starts[1:] + [total]

    if v.clips.exists():
        shutil.rmtree(v.clips)
    v.clips.mkdir(parents=True)
    timing = {}
    for sc, a, b, c in zip(v.scenes, starts, ends, found):
        sh("ffmpeg", "-y", "-v", "error", "-i", voice, "-ss", f"{a:.3f}", "-to", f"{b:.3f}", v.clips / f"{sc.name}.wav")
        timing[sc.name] = {
            "start": round(a, 3),
            "length": round(b - a, 3),
            "cues": {k: round(max(0.0, tc - a), 3) for k, (tc, _) in c.items()},
        }
        print(f"\n{sc.name}  {clock(a)}  ({b - a:.1f} s)")
        for k, (tc, heard) in c.items():
            print(f"  {tc - a:6.1f} s  {k:<16} «{heard} …»")
    v.timing_file.write_text(json.dumps(timing, ensure_ascii=False, indent=1))
    print(f"\n✓ {len(v.scenes)} scenes, {sum(len(c) for c in found)} cues, {clock(total)} of speech.")
    print(f"  Wrote {rel(v.timing_file)} and {rel(v.clips)}/. Next: ./pipeline render {v.slug}")


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
def _literal_strings(node):
    if isinstance(node, (ast.Tuple, ast.List)):
        out = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        return out if len(out) == len(node.elts) else None
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "enumerate" and node.args:
        return _literal_strings(node.args[0])
    return None


def _loop_bindings(func):
    """Names bound by ``for x in ("a", "b")`` (or enumerate of it) in ``func``."""
    out = {}
    for node in ast.walk(func):
        if isinstance(node, ast.For):
            values = _literal_strings(node.iter)
            if values is None:
                continue
            target = node.target
            if isinstance(target, ast.Tuple) and isinstance(node.iter, ast.Call) and len(target.elts) == 2:
                target = target.elts[1]
            if isinstance(target, ast.Name):
                out.setdefault(target.id, []).extend(values)
    return out


def _cue_calls(classes, name, seen=None):
    """(cue names used, has dynamic cue names) in class ``name`` and its local bases."""
    seen = seen or set()
    if name in seen or name not in classes:
        return set(), False
    seen.add(name)
    cls = classes[name]
    used, dynamic = set(), False
    for func in [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        loops = _loop_bindings(func)
        for node in ast.walk(func):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "cue"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "self"
                and node.args
            ):
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    used.add(arg.value)
                elif isinstance(arg, ast.Name) and arg.id in loops:
                    used |= set(loops[arg.id])
                else:
                    dynamic = True
    for base in cls.bases:
        if isinstance(base, ast.Name):
            u, d = _cue_calls(classes, base.id, seen)
            used |= u
            dynamic |= d
    return used, dynamic


def timing_is_stale(v):
    """Why timing.json no longer matches video.toml and the recordings ([] if it does)."""
    if not v.timing_file.exists():
        return []
    reasons = []
    stamp = v.timing_file.stat().st_mtime
    newer = [f.name for f in [v.folder / "video.toml", *recordings(v, strict=False)] if f.stat().st_mtime > stamp]
    if newer:
        reasons.append(f"timing.json is older than {', '.join(newer)}: run sync again")
    timing = v.timing()
    for sc in v.scenes:
        if sc.name not in timing:
            reasons.append(f"Scene {sc.name} has no timing yet: run sync again")
        elif set(timing[sc.name]["cues"]) != set(sc.cues):
            reasons.append(f"Scene {sc.name}: the cues changed since the last sync: run sync again")
    return reasons


def report(errors, warnings):
    for w in warnings:
        print(f"  ! {w}")
    for e in errors:
        print(f"  ✗ {e}")


def check(v):
    """(errors, warnings) for a video. Errors stop a render; warnings don't."""
    errors, warnings = [], []
    names = v.scene_names
    for n in {n for n in names if names.count(n) > 1}:
        errors.append(f"Scene {n} is listed twice in video.toml")
    for i, sc in enumerate(v.scenes):
        if i > 0 and not sc.start:
            errors.append(f"Scene {sc.name} needs a start phrase (only the first scene may omit it)")
        for cue, (phrase, _) in sc.cues.items():
            if not phrase.strip():
                errors.append(f"Scene {sc.name}: cue {cue} has an empty phrase")
    if not v.scenes:
        warnings.append("video.toml has no scenes yet")

    if not v.scenes_file.exists():
        errors.append(f"{rel(v.scenes_file)} is missing")
    else:
        try:
            tree = ast.parse(v.scenes_file.read_text())
        except SyntaxError as e:
            errors.append(f"{rel(v.scenes_file)}:{e.lineno}: {e.msg}")
            tree = None
        if tree:
            classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
            concrete = [
                n for n, c in classes.items()
                if any(isinstance(f, ast.FunctionDef) and f.name == "construct" for f in c.body)
            ]
            for sc in v.scenes:
                if sc.name not in classes:
                    errors.append(f"Scene {sc.name} is in video.toml but has no class in scenes.py")
                    continue
                used, dynamic = _cue_calls(classes, sc.name)
                for cue in sorted(used - set(sc.cues)):
                    errors.append(f"{sc.name} waits for cue {cue!r}, which is not in video.toml")
                if not dynamic:
                    for cue in sc.cues:
                        if cue not in used:
                            warnings.append(f"{sc.name}: cue {cue!r} in video.toml is never waited for")
            for n in concrete:
                if n not in names:
                    warnings.append(f"Class {n} in scenes.py is not listed in video.toml, so it is never rendered")

    markers = len(MARKER.findall(manuscript_text(v)))
    if isinstance(v.cfg["recordings"], list):
        missing = [n for n in v.cfg["recordings"] if not (v.audio / n).exists()]
        if missing:
            warnings.append(f"Listed in recordings but not in audio/: {', '.join(missing)}")
    files = recordings(v, strict=False)
    if files and markers and len(files) != markers:
        warnings.append(f"{len(files)} recordings for {markers} animation markers in the manuscript")
    warnings += timing_is_stale(v)
    return errors, warnings


def cmd_check(v, args):
    errors, warnings = check(v)
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            errors.append(f"{tool} is not installed")
    try:
        sys.path.insert(0, str(ENGINE))
        import kit  # noqa: F401  (also checks that Manim and the theme load)

        print(f"  fonts: {kit.SANS or '(default)'} / {kit.MONO}")
    except Exception as e:  # pragma: no cover - depends on the machine
        errors.append(f"engine/kit.py does not load: {e}")
    report(errors, warnings)
    files = recordings(v, strict=False)
    print(f"  {len(v.scenes)} scenes, {sum(len(s.cues) for s in v.scenes)} cues, {len(files)} recordings")
    if errors:
        die(f"{len(errors)} error(s)")
    print("✓ ok" + (f" ({len(warnings)} warning(s))" if warnings else ""))


# --------------------------------------------------------------------------
# Render, stills, assemble
# --------------------------------------------------------------------------
def _rendered_log(v):
    f = v.build / "rendered.json"
    return json.loads(f.read_text()) if f.exists() else {}


def _timing_key(entry):
    """What a render depends on in a scene's timing (not where the scene starts)."""
    if not entry:
        return None
    key = {"length": entry["length"], "cues": entry["cues"]}
    return hashlib.sha1(json.dumps(key, sort_keys=True).encode()).hexdigest()


def cmd_render(v, args):
    errors, _ = check(v)
    if errors:
        report(errors, [])
        die("Fix these first (./pipeline check)")
    names = args.scenes or v.scene_names
    unknown = [n for n in names if n not in v.scene_names]
    if unknown:
        die(f"Unknown scene(s): {', '.join(unknown)}. Scenes: {', '.join(v.scene_names)}")
    flag, qdir = QUALITY[args.quality]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ENGINE), os.environ.get("PYTHONPATH", "")]))
    base = [sys.executable, "-m", "manim", "render", flag, "--media_dir", str(v.media),
            "--progress_bar", "none", "-v", "WARNING", str(v.scenes_file)]
    timing = v.timing()
    print(f"Rendering {len(names)} scene(s) of {v.slug} at {qdir}" + (" with audio" if timing else " (no timing yet)"))

    def one(name):
        cmd = base + [name]
        if args.jobs > 1:
            # Manim caches text as SVG files in one shared folder, and parallel
            # renders of the same caption trip over each other's temp files.
            # Each scene gets its own text cache instead.
            cfg = v.build / "tmp" / f"{name}.cfg"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(f"[CLI]\ntext_dir = {v.media / 'texts' / name}\n")
            cmd[4:4] = ["--config_file", str(cfg)]
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=v.folder)
        return name, r.returncode, r.stdout + r.stderr, time.time() - t0

    log = _rendered_log(v)
    late, failed = [], []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for name, code, out, secs in pool.map(one, names):
            notes = [ln for ln in out.splitlines() if ln.startswith("[timing]")]
            late += notes
            if code != 0:
                failed.append(name)
                print(f"  ✗ {name} failed after {secs:.0f} s:\n" + "\n".join(out.strip().splitlines()[-25:]))
                continue
            log.setdefault(qdir, {})[name] = _timing_key(timing.get(name))
            print(f"  ✓ {name}  ({secs:.0f} s)" + "".join(f"\n    {n}" for n in notes), flush=True)
    v.build.mkdir(parents=True, exist_ok=True)
    (v.build / "rendered.json").write_text(json.dumps(log, indent=1))
    if late:
        print("\nTiming warnings: shorten run_time (or move animations after the cue) where a cue comes late.")
    if failed:
        die(f"{len(failed)} scene(s) failed: {', '.join(failed)}")
    print(f"✓ Rendered to {rel(v.rendered(args.quality))}/")


def _stale_scenes(v, q):
    """Scenes whose render was made with other timing than the current one."""
    timing, log = v.timing(), _rendered_log(v).get(QUALITY[q][1], {})
    return [n for n in v.scene_names if n in log and log[n] != _timing_key(timing.get(n))]


def cmd_stills(v, args):
    names = args.scenes or v.scene_names
    folder = v.rendered(args.quality)
    timing = v.timing()
    out = v.build / "stills"
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for name in names:
        mp4 = folder / f"{name}.mp4"
        if not mp4.exists():
            print(f"  - {name}: not rendered at {QUALITY[args.quality][1]}")
            continue
        for old in out.glob(f"{name}_*.png"):
            old.unlink()
        length = video_length(mp4)
        # The settled picture just before each change is what viewers see longest.
        points = [("start", 0.0)]
        cues = sorted(timing.get(name, {}).get("cues", {}).items(), key=lambda kv: kv[1]) if timing.get(name) else []
        if cues:
            times = [t for _, t in cues] + [length - 1.0]
            points += [(c, max(0.0, nxt - 0.1)) for (c, _), nxt in zip(cues, times[1:])]
        else:
            n = max(3, int(length // 2.5))
            points += [(f"{length * i / n:.0f}s", length * i / n) for i in range(1, n)]
        points.append(("last", length))
        frames = []
        for i, (lab, t) in enumerate(points):
            safe = re.sub(r"[^\w]", "", lab)
            png = out / f"{name}_{i:02d}_{safe}.png"
            if lab == "last":
                # Read the final second and keep overwriting: the last frame wins.
                sh("ffmpeg", "-y", "-v", "error", "-sseof", "-1", "-i", mp4, "-update", "1", "-vf", "scale=960:-2", png)
            else:
                sh("ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", mp4, "-frames:v", "1", "-vf", "scale=960:-2", png)
            if png.exists():
                frames.append((png, f"{name} · {lab} · {t:.1f} s"))
        sheet = out / f"{name}_sheet.png"
        _contact_sheet(frames, sheet)
        made.append(sheet)
        print(f"  {name}: {len(frames)} frames → {rel(sheet)}")
    if made:
        print(f"✓ Stills in {rel(out)}/ (one *_sheet.png per scene, single frames beside it)")


def _contact_sheet(frames, path, cols=2):
    from PIL import Image, ImageDraw, ImageFont

    imgs = [Image.open(p).convert("RGB") for p, _ in frames]
    w, h = imgs[0].size
    bar = 34
    rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + bar)), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=22)
    except TypeError:  # Pillow < 10.1
        font = ImageFont.load_default()
    for i, (img, (_, caption)) in enumerate(zip(imgs, frames)):
        x, y = (i % cols) * w, (i // cols) * (h + bar)
        draw.text((x + 10, y + 6), caption, fill="black", font=font)
        sheet.paste(img, (x, y + bar))
    sheet.save(path)


def cmd_assemble(v, args):
    q = args.quality
    folder = v.rendered(q)
    missing = [n for n in v.scene_names if not (folder / f"{n}.mp4").exists()]
    if missing:
        die(f"Not rendered at {QUALITY[q][1]}: {', '.join(missing)}. Run ./pipeline render {v.slug} -q {q}")
    timing = v.timing()
    if timing:
        no_timing = [n for n in v.scene_names if n not in timing]
        if no_timing:
            die(f"No timing for {', '.join(no_timing)}: run ./pipeline sync {v.slug}")
        stale = _stale_scenes(v, q)
        if stale:
            die(f"Rendered with older timing: {', '.join(stale)}. Run ./pipeline render {v.slug} {' '.join(stale)} -q {q}")

    tmp = v.build / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    listing = tmp / "scenes.txt"
    listing.write_text("".join(f"file '{folder / n}.mp4'\n" for n in v.scene_names))
    out = v.output(q)
    out.parent.mkdir(exist_ok=True)

    if not timing:
        print("No timing yet: assembling the picture without sound.")
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", listing,
           "-map", "0:v", "-c:v", "copy", "-movflags", "+faststart", out)
    else:
        # Manim can give a scene one frame less than its audio clip. Each clip
        # is therefore cut to exactly its scene's picture length, so sync is
        # reset at every scene boundary instead of drifting through the video.
        clips = []
        for i, n in enumerate(v.scene_names):
            k = tmp / f"clip{i}.wav"
            sh("ffmpeg", "-y", "-v", "error", "-i", v.clips / f"{n}.wav",
               "-af", f"apad,atrim=0:{video_length(folder / f'{n}.mp4'):.4f}", "-ar", "48000", "-ac", "2", k)
            clips.append(k)
        audio_list = tmp / "clips.txt"
        audio_list.write_text("".join(f"file '{k.name}'\n" for k in clips))
        track = tmp / "track.wav"
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", audio_list, "-c", "copy", track)
        sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", listing, "-i", track,
           "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out)
    shutil.rmtree(tmp)

    picture = video_length(out)
    line = f"✓ {rel(out)}: {clock(picture)}, {out.stat().st_size / 1e6:.0f} MB"
    if timing:
        sound = audio_length(out)
        line += f"; picture {picture:.2f} s, sound {sound:.2f} s"
        if abs(picture - sound) > 0.1:
            line += "  ← mismatch, check the scenes' endings"
    print(line)


def cmd_preview(v, args):
    args.quality = "l"
    cmd_render(v, args)
    if not args.scenes:
        cmd_assemble(v, args)
    cmd_stills(v, args)


def cmd_build(v, args):
    cmd_sync(v, args)
    args.quality, args.scenes = "h", []
    cmd_render(v, args)
    cmd_assemble(v, args)


# --------------------------------------------------------------------------
# Status and new videos
# --------------------------------------------------------------------------
def video_status(slug):
    row = dict.fromkeys(["manuscript", "scenes", "recordings", "timing", "rendered", "output"], "")
    row["video"] = slug
    try:
        v = load(slug)
    except SystemExit:
        row["next"] = "fix video.toml (see the error above)"
        return row
    text = manuscript_text(v)
    words = len(re.sub(r"```.*?```", "", text, flags=re.S).split())
    row["manuscript"] = f"{words} words, {len(MARKER.findall(text))} markers" if text else "–"
    row["scenes"] = str(len(v.scenes))
    files = recordings(v, strict=False)
    done = sum(1 for f in files if is_transcribed(v, f))
    row["recordings"] = f"{len(files)} ({done} transcribed)" if files else "–"
    timing = v.timing()
    errors, _ = check(v)
    stale_timing = bool(timing_is_stale(v))
    row["timing"] = ("stale" if stale_timing else "✓") if timing else "–"
    renders = []
    for q, (_, qdir) in QUALITY.items():
        folder = v.rendered(q)
        n = sum(1 for s in v.scene_names if (folder / f"{s}.mp4").exists())
        if n:
            stale = len(_stale_scenes(v, q))
            renders.append(f"{qdir} {n}/{len(v.scenes)}" + (f" ({stale} stale)" if stale else ""))
    row["rendered"] = ", ".join(renders) or "–"
    out = v.output("h")
    row["output"] = f"{clock(video_length(out))}, {time.strftime('%d.%m %H:%M', time.localtime(out.stat().st_mtime))}" if out.exists() else "–"

    hq = v.rendered("h")
    if errors:
        nxt = "fix the errors from ./pipeline check"
    elif words < 30:
        nxt = "write the manuscript"
    elif not v.scenes:
        nxt = "plan and animate the scenes"
    elif not files:
        nxt = "preview the animations, then record"
    elif not timing or stale_timing:
        nxt = "sync"
    elif any(not (hq / f"{s}.mp4").exists() for s in v.scene_names) or _stale_scenes(v, "h"):
        nxt = "render"
    elif not out.exists() or out.stat().st_mtime < max((hq / f"{s}.mp4").stat().st_mtime for s in v.scene_names):
        nxt = "assemble"
    else:
        nxt = "done: watch it and give feedback"
    row["next"] = nxt
    return row


def cmd_status(args):
    slugs = [args.slug] if args.slug else all_slugs()
    if not slugs:
        print("No videos yet. Start one with ./pipeline new <slug>")
        return
    rows = [video_status(s) for s in slugs]
    cols = ["video", "manuscript", "scenes", "recordings", "timing", "rendered", "output", "next"]
    widths = {c: max(len(c), *(len(r[c]) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    print("  ".join("-" * widths[c] for c in cols))
    for r in rows:
        print("  ".join(r[c].ljust(widths[c]) for c in cols))


def cmd_new(args):
    slug = args.slug
    if not re.fullmatch(r"[a-z0-9][a-z0-9_]*", slug):
        die("Use lower case letters, digits and _ in the slug, e.g. generics_intro")
    target = VIDEOS / slug
    if target.exists():
        die(f"{rel(target)} already exists")
    shutil.copytree(VIDEOS / "_skeleton", target)
    title = args.title or slug.replace("_", " ").capitalize()
    for f in target.rglob("*"):
        if f.is_file() and f.suffix in (".md", ".toml", ".py"):
            f.write_text(f.read_text().replace("{{TITLE}}", title).replace("{{SLUG}}", slug))
    (target / "audio").mkdir(exist_ok=True)
    print(f"✓ Created {rel(target)}/: manuscript.md, plan.md, video.toml, scenes.py, audio/")


# --------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(prog="./pipeline", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, help, scenes=False, quality=None):
        s = sub.add_parser(name, help=help)
        s.add_argument("slug")
        if scenes:
            s.add_argument("scenes", nargs="*", help="only these scenes (default: all)")
        if quality:
            s.add_argument("-q", "--quality", choices=QUALITY, default=quality,
                           help="l=480p15 m=720p30 h=1080p60 p=1440p60 k=2160p60")
        return s

    s = sub.add_parser("status", help="where every video is in the process")
    s.add_argument("slug", nargs="?")
    s = sub.add_parser("new", help="a new video folder from videos/_skeleton")
    s.add_argument("slug")
    s.add_argument("--title")
    add("check", "validate video.toml against scenes.py, manuscript and recordings")
    add("render", "render scenes", scenes=True, quality="h").add_argument("-j", "--jobs", type=int, default=1)
    add("preview", "render at 480p15, assemble a preview and take stills", scenes=True).add_argument(
        "-j", "--jobs", type=int, default=1)
    add("stills", "PNG frames at every cue", scenes=True, quality="l")
    add("transcript", "transcribe the recordings and show the text")
    add("sync", "timing.json + one audio clip per scene").add_argument("--fuzzy", action="store_true")
    add("assemble", "join scenes + voice into output/", quality="h")
    s = add("build", "sync, render at 1080p60 and assemble")
    s.add_argument("--fuzzy", action="store_true")
    s.add_argument("-j", "--jobs", type=int, default=1)

    args = p.parse_args()
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "new":
        return cmd_new(args)
    v = load(args.slug)
    {
        "check": cmd_check, "render": cmd_render, "preview": cmd_preview, "stills": cmd_stills,
        "transcript": cmd_transcript, "sync": cmd_sync, "assemble": cmd_assemble, "build": cmd_build,
    }[args.cmd](v, args)


if __name__ == "__main__":
    main()
