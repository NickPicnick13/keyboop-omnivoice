# Keyboop + OmniVoice Kit

**A local keyboard-layout and AI voice setup for macOS.** [Русская инструкция](README.ru.md)

Two separate upstream projects: [Keyboop](https://keyboop.com) switches/fixes keyboard layouts; [OmniVoice](https://github.com/k2-fsa/OmniVoice) synthesizes an AI agent's speech. This repository provides an independent, localhost-only voice API and setup guide. It **does not** redistribute either upstream project, pretrained weights or people's voice recordings.

## Quick start (Apple Silicon, macOS)

1. Install official [Keyboop](https://keyboop.com), grant macOS Accessibility/Input Monitoring permissions as prompted, and configure your language layouts in Keyboop settings.
2. Have **Python 3.11** and **3 GB+** free disk space for OmniVoice weights (plus Python dependencies). On an Apple Silicon Mac with PyTorch MPS:
   ```sh
   git clone https://github.com/NickPicnick13/keyboop-omnivoice.git
   cd keyboop-omnivoice
   bash scripts/install.sh
   ```
3. Download the OmniVoice pretrained weights yourself following [upstream instructions](https://github.com/k2-fsa/OmniVoice); set `KOV_MODEL_DIR` to the directory containing `model.safetensors`.
4. Register an **authorized** reference sample, with an *exact transcript* of what was spoken:
   ```sh
   source .venv/bin/activate
   keyboop-omnivoice add-voice narrator --file /path/to/consented-sample.wav --text "Exact words in the sample"
   keyboop-omnivoice serve
   ```
   Alternatively: `keyboop-omnivoice add-design narrator --instruction "A warm, clear Russian narrator"`.
5. In another terminal, try:
   ```sh
   curl -sS http://127.0.0.1:3912/health
   curl -sS http://127.0.0.1:3912/v1/audio/speech -H 'Content-Type: application/json' -d '{"voice":"narrator","input":"Привет! Это мой агент."}' --output speech.wav
   ```
   Play `speech.wav` locally. Point your agent's OpenAI-compatible TTS client at `http://127.0.0.1:3912/v1/audio/speech`. The API uses `voice` and `input`, returns WAV. Existing services are not modified.

### Commands

`keyboop-omnivoice doctor` checks runtime prerequisites; `list-voices` lists your local profiles; `add-voice` registers a consented WAV sample; `add-design` creates an instruction-based voice; `remove-voice` deletes a profile; `serve` starts the localhost-only API. Run `keyboop-omnivoice --help` for options. Data are held in `~/.local/share/keyboop-omnivoice` and `~/.config/keyboop-omnivoice`, never in Git.

### Caveats

This is an **alpha integration**, not a signed macOS app or Keyboop replacement. It is tested at the API/unit level; end-to-end installation on a fresh Mac has not yet been certified. The model starts cold and can take time to load. The server has **no authentication**; do not expose port 3912 on your network. Only use voices with their owners' consent. **The published model weights have a noncommercial license**; see [THIRD_PARTY.md](THIRD_PARTY.md). [Security](SECURITY.md), [Contributing](CONTRIBUTING.md).

Keyboop and OmniVoice are separate products and this kit is not affiliated with their developers.
