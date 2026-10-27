# Contributing

This is an independent integration project. Changes to Keyboop's switching engine belong in [the upstream project](https://github.com/iffuno/keyboop). Changes to the OmniVoice model belong upstream.

1. Use Python 3.11 or 3.12.
2. Run `python -m pip install -e ".[test]"` and `python -m pytest -q`.
3. Check shell syntax with `bash -n scripts/install.sh scripts/uninstall.sh`.
4. Do not commit reference audio, transcripts, weights, secrets, personal configuration or absolute user-specific paths. Keep sample voices synthetic in tests.
5. Test installer changes with `bash scripts/install.sh --dry-run` before any real installation.

License: MIT for code contributed to this repository; all upstream software keeps its own license.
