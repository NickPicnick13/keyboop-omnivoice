#!/usr/bin/env python3
"""Start the real local HTTP server in an ephemeral sandbox; no model or user data needed."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="kov-http-smoke-") as folder:
    env=os.environ.copy()
    env["KOV_CONFIG_DIR"]=folder+"/config"
    env["KOV_DATA_DIR"]=folder+"/data"
    # Reserve then free a loopback ephemeral port; minimize conflicts.
    sock=socket.socket()
    sock.bind(("127.0.0.1",0))
    port=sock.getsockname()[1]
    sock.close()
    base=f"http://127.0.0.1:{port}"
    proc=subprocess.Popen([sys.executable,"-m","keyboop_omnivoice.cli","serve","--port",str(port)],
                          env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    try:
        for _ in range(60):
            if proc.poll() is not None:
                raise RuntimeError("Server exited unexpectedly: "+proc.stderr.read()[-500:])
            try:
                with urllib.request.urlopen(base+"/health",timeout=1) as response:
                    health=json.load(response)
                break
            except OSError:
                time.sleep(0.15)
        else: raise RuntimeError("HTTP server did not become ready")
        assert health["ok"] and not health["model_downloaded"]
        payload=json.dumps({"name":"narrator","instruction":"female, moderate pitch",
                            "language":"Russian"}).encode("utf8")
        req=urllib.request.Request(base+"/api/voices/design",payload,{"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=2) as response:
            assert response.status==201
        with urllib.request.urlopen(base+"/api/voices",timeout=2) as response:
            assert json.load(response)["voices"][0]["name"]=="narrator"
        with urllib.request.urlopen(base+"/",timeout=2) as response:
            assert b"Keyboop + OmniVoice" in response.read()
        print("HTTP_SMOKE_OK: localhost API, web dashboard, profile creation")
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)
