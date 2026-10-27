# Security

The HTTP server binds to **127.0.0.1** only, and does **not** have authentication. Never publish it via tunnels, reverse proxies, port forwarding or a 0.0.0.0 binding without implementing authentication and rate limiting.

Private voice profiles, reference samples and model data live **outside this Git repository**, under your home directory by default. No voice text or generated audio is intentionally written to logs. A small in-memory response cache may hold synthesized speech until process exit; there is no disk cache.

Only clone voices with explicit owner consent. Initial Python package installation and model download use the internet; model inference itself is local after downloading. No cloud TTS API is invoked by this kit.

Open a sanitized issue for bugs. Never paste private voice clips, transcripts, keys or tokens into public issues.
