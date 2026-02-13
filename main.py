"""
Cerebrium Serverless App for Demucs Audio Separation.

Reuses the existing serverless Docker image (models baked-in).
Exposes a FastAPI POST endpoint that runs demucs-separate.

Deploy:
    cerebrium login
    cerebrium deploy

Test:
    curl -X POST <endpoint_url>/run \
      -H "Content-Type: application/json" \
      -d '{"api_key": "...", "audio_url": "...", "id_projet": "...", "upload_token": "...", "worker_url": "..."}'
"""

import os
import subprocess
import json
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI

app = FastAPI()

API_KEY = os.environ.get("CEREBRIUM_API_KEY", "")


@app.get("/health")
def health():
    models = list(Path("/models-cache").glob("*"))
    return {"status": "ok", "models": len(models)}


@app.get("/ready")
def ready():
    models = list(Path("/models-cache").glob("*"))
    if len(models) == 0:
        return {"status": "not ready"}, 503
    return {"status": "ready"}


@app.post("/run")
def run(input_data: dict):
    """Run demucs-separate and return the result."""
    # Auth check
    if API_KEY:
        if input_data.get("api_key") != API_KEY:
            return {"error": "unauthorized"}

    audio_url = input_data.get("audio_url")
    id_projet = input_data.get("id_projet")
    upload_token = input_data.get("upload_token")
    worker_url = input_data.get("worker_url")
    vram_gb = input_data.get("vram_gb")
    all_stems = input_data.get("all_stems", False)

    if not audio_url:
        return {"error": "audio_url is required"}
    if not upload_token or not worker_url:
        return {"error": "upload_token and worker_url are required"}

    job_dir = Path(tempfile.mkdtemp(prefix="demucs-cerebrium-"))
    try:
        # Write R2 config for demucs-separate
        with open(job_dir / "r2_config.json", "w") as f:
            json.dump({
                "upload_token": upload_token,
                "worker_url": worker_url,
                "id_projet": id_projet,
            }, f)

        cmd = ["demucs-separate", "--audio-url", audio_url, "--output", str(job_dir)]
        if id_projet:
            cmd.extend(["--id-projet", id_projet])
        if vram_gb:
            cmd.extend(["--vram-gb", str(vram_gb)])
        if all_stems:
            cmd.append("--all-stems")

        print(f"[cerebrium] Running: {' '.join(cmd)}", flush=True)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in process.stdout:
            print(line, end="", flush=True)
        process.wait()

        if process.returncode == 0:
            print("[cerebrium] Job completed successfully", flush=True)
            return {"status": "completed", "id_projet": id_projet}
        else:
            print(f"[cerebrium] Job failed (exit {process.returncode})", flush=True)
            return {"error": f"demucs-separate failed (exit {process.returncode})"}

    except Exception as e:
        print(f"[cerebrium] Error: {e}", flush=True)
        return {"error": str(e)}

    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
