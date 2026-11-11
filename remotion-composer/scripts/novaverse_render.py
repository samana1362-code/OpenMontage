#!/usr/bin/env python3
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

REPLACEMENTS = {
    "hemesanin": "hemocyanin",
    "hemosanin": "hemocyanin",
}

def run(cmd):
    subprocess.run(cmd, check=True)

def seconds_to_ass(value):
    cs = max(0, round(value * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"

def clean_word(word):
    key = re.sub(r"[^a-z]", "", word.lower())
    replacement = REPLACEMENTS.get(key)
    if replacement:
        return replacement + re.sub(r"[A-Za-z]", "", word)
    return word

def make_captions(words, output, font_size):
    groups = []
    current = []

    for item in words:
        if current:
            pause = item["start"] - current[-1]["end"]
            phrase = " ".join(w["text"] for w in current)
            if pause > 0.55 or len(current) >= 5 or len(phrase) > 34:
                groups.append(current)
                current = []
        current.append(item)

    if current:
        groups.append(current)

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,%d,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,8,90,90,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" % font_size

    with open(output, "w", encoding="utf-8") as f:
        f.write(header)
        for group in groups:
            start = max(0, group[0]["start"] - 0.04)
            end = group[-1]["end"] + 0.12
            text = " ".join(w["text"] for w in group)
            text = text.replace("{", r"\{").replace("}", r"\}")
            f.write(
                f"Dialogue: 0,{seconds_to_ass(start)},{seconds_to_ass(end)},"
                f"Default,,0,0,0,,{text}\n"
            )

def parse_scene(value):
    try:
        path, duration = value.rsplit(":", 1)
        path = Path(path).expanduser().resolve()
        duration = float(duration)
    except Exception:
        raise argparse.ArgumentTypeError("Scene format must be PATH:DURATION")
    if not path.is_file() or duration <= 0:
        raise argparse.ArgumentTypeError(f"Invalid scene: {value}")
    return path, duration

def main():
    parser = argparse.ArgumentParser(
        description="NovaVerse vertical video renderer"
    )
    parser.add_argument("--audio", required=True)
    parser.add_argument("--scene", action="append", required=True,
                        type=parse_scene, help="Video path and duration: PATH:SECONDS")
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="base.en")
    parser.add_argument("--font-size", type=int, default=48)
    args = parser.parse_args()

    audio = Path(args.audio).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not audio.is_file():
        parser.error(f"Audio file not found: {audio}")
    output.parent.mkdir(parents=True, exist_ok=True)

    probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio)
    ], text=True)
    audio_duration = float(probe.strip())

    print("1/4 - Transcribing and aligning narration...")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(audio), word_timestamps=True, vad_filter=False
    )
    words = []
    for segment in segments:
        for word in segment.words or []:
            text = clean_word(word.word.strip())
            if text and word.start is not None and word.end is not None:
                words.append({
                    "start": float(word.start),
                    "end": float(word.end),
                    "text": text,
                })

    if not words:
        raise RuntimeError("Whisper returned no word timestamps.")

    print(f"   Found {len(words)} words; audio is {audio_duration:.2f}s")
    subtitle_file = output.with_suffix(".ass")
    make_captions(words, subtitle_file, args.font_size)

    print("2/4 - Preparing vertical footage...")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        clip_files = []
        remaining = audio_duration

        for index, (scene_path, requested_duration) in enumerate(args.scene):
            if remaining <= 0:
                break
            duration = min(requested_duration, remaining)
            clip = temp / f"scene_{index:03d}.mp4"
            run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(scene_path), "-t", f"{duration:.3f}",
                "-an", "-vf",
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,fps=30,setsar=1",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-r", "30",
                str(clip)
            ])
            clip_files.append(clip)
            remaining -= duration

        if remaining > 0.15:
            raise RuntimeError(
                f"Scenes are {remaining:.2f}s too short for the narration."
            )

        concat_file = temp / "concat.txt"
        concat_file.write_text(
            "".join(f"file '{p.as_posix()}'\n" for p in clip_files),
            encoding="utf-8"
        )
        silent_video = temp / "silent.mp4"
        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-c", "copy", str(silent_video)
        ])

        print("3/4 - Burning synchronized subtitles...")
        ass_path = subtitle_file.resolve().as_posix()
        ass_path = ass_path.replace("\\", "\\\\").replace(":", "\\:")
        ass_path = ass_path.replace("'", "\\'")
        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(silent_video), "-i", str(audio),
            "-vf", f"ass='{ass_path}'",
            "-map", "0:v:0", "-map", "1:a:0",
            "-t", f"{audio_duration:.3f}",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", str(output)
        ])

    print("4/4 - Complete!")
    print(f"Video: {output}")
    print(f"Subtitles: {subtitle_file}")

if __name__ == "__main__":
    main()
