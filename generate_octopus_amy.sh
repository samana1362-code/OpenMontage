#!/usr/bin/env bash
set -euo pipefail

# OpenMontage / NovaVerse — one-off Amy narration generator
# Creates a WAV in the episode folder without changing Nova's existing audio.

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

EPISODE_DIR="projects/novaverse/episodes/octopus-three-hearts"
mkdir -p "$EPISODE_DIR"

cat > "$EPISODE_DIR/narration.txt" <<'TEXT'
An octopus has three hearts. Two pump blood through its gills. The third sends oxygen-rich blood around the body.

And its blood? Blue. Instead of iron-based hemoglobin, an octopus uses a copper-rich protein called hemocyanin to carry oxygen.

Its nervous system is just as unusual. A large share of its neurons are distributed through its eight arms, giving them remarkable local control—while the brain still coordinates the animal.

And here's one more twist: when an octopus swims, its main systemic heart temporarily stops beating. That's one reason swimming can be exhausting, and crawling is often preferred.

Three hearts, blue blood, and arms with a mind of their own. What other animal can top that?
TEXT

# Use a separate virtual environment so the project's existing dependencies stay untouched.
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -m venv .venv-piper
PIPER_PY=".venv-piper/bin/python"
PIPER_BIN=".venv-piper/bin/piper"

"$PIPER_PY" -m pip install --upgrade pip
"$PIPER_PY" -m pip install piper-tts

# Download the Amy model and its configuration into Piper's voice cache.
"$PIPER_PY" -m piper.download_voices en_US-amy-medium

# Generate the episode narration.
"$PIPER_BIN" \
  --model en_US-amy-medium \
  --output_file "$EPISODE_DIR/narration.wav" \
  < "$EPISODE_DIR/narration.txt"

echo
echo "SUCCESS: $EPISODE_DIR/narration.wav"
echo "Listen to the WAV before using it in the video."
