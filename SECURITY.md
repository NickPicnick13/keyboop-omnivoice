# Security and privacy

- The TTS API listens only on `127.0.0.1:3912`, without authentication. **Do not expose it** through a network proxy, tunnel, SSH port forward or binding to `0.0.0.0`. A program running locally may call it.
- Voice samples and transcripts are in a private user folder, with user-only filesystem permissions; no private voice sample or downloaded weight is checked into Git.
- The installer asks the user to accept the official **CC-BY-NC** terms before downloading weights. No model weights or third-party binary code ship in the release ZIP.
- Keyboop comes directly from the upstream GitHub release, with asset integrity checks and Apple signature assessment. The installer never modifies an existing named Keyboop.app and does not bypass macOS Accessibility/Input Monitoring prompts.
- Python and model downloads contact package registries and Hugging Face. After installation the TTS API performs local generation; no cloud TTS is used.
- The API refuses foreign browser Origins and Hosts, uses bounded requests and a small queue, and stores only a bounded response cache in memory. Server logs do not intentionally record transcribed or synthesized text.
- The launcher is a transparent `.command` script and **not notarized**. Inspect before executing. The macOS Gatekeeper warning for the launcher must not be bypassed programmatically.
- Only clone a voice with its owner's explicit consent. Do not use for impersonation, scams, or unauthorized speaker imitation.

For security issues, please report without exposing voice recordings, tokens, private file paths or transcripts.
