# Keyboop + OmniVoice

A **downloadable macOS setup kit** for two independent tools: [Keyboop](https://keyboop.com), the free keyboard layout switcher, and [OmniVoice](https://github.com/k2-fsa/OmniVoice), the local AI-agent text-to-speech engine.

[Русская инструкция](README.md) · [Releases](https://github.com/NickPicnick13/keyboop-omnivoice/releases)

## Installation

1. Download the release ZIP from **Releases**, extract it on an Apple Silicon Mac (M1+, macOS 14+).
2. Double-click **Install.command**. If macOS blocks an unsigned downloaded script, inspect it, then right-click → Open if you trust it.
3. Review and accept the **CC-BY-NC noncommercial license** for the pretrained OmniVoice model. The installer downloads the official signed Keyboop DMG, installs Python/OmniVoice and downloads the 3.3 GB model weights.
4. A localhost dashboard opens at **http://127.0.0.1:3912/**. Try the included narrator voice, design a voice with supported attributes (gender/pitch/accent), or clone a consenting person's voice from a short PCM WAV and accurate transcript.
5. Grant Keyboop Accessibility/Input Monitoring permissions when macOS prompts you. No tool may bypass the permissions dialog.

The voice server runs at login. Keyboard switching and voice synthesis are **separate components**.

### Agent API

A subset of the OpenAI TTS interface is implemented: `POST http://127.0.0.1:3912/v1/audio/speech`, JSON `{"voice":"narrator","input":"Hello there.","response_format":"wav"}`, WAV response. The service listens **only on localhost** and is not network authenticated. Do not expose its port.

### Management

- **Open Dashboard.command** — browser control panel.
- **Remove.command** — uninstall the integration; leave private voices untouched.
- Models, voice samples and transcripts are kept in private user folders, outside Git.
- Repeat installation to repair a partial download; it is designed to be idempotent.
- Requires several GB of disk space and enough unified memory for local TTS. 16 GB RAM or more recommended.

### Licensing and limitations

This integration: MIT. Keyboop: MIT; owned and maintained independently by Ivan Smetanin. OmniVoice software: Apache-2.0. **OmniVoice model weights: CC BY-NC, noncommercial only**. Never clone a person's voice without their consent or impersonate others. Neither upstream product nor its weights or any private audio is bundled in the ZIP.

**Beta:** the installer and API have local tests; a clean-machine end-to-end install remains to be certified. This ZIP is not a notarized self-contained Mac app.

[Third-party licenses](THIRD_PARTY.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)
