#!/usr/bin/env python
import os
import shutil
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT, "frontend")
DIST = os.path.join(FRONTEND_DIR, "dist")
WIN = sys.platform == "win32"

PYTHON = os.path.join(ROOT, ".venv", "Scripts" if WIN else "bin", "python" + (".exe" if WIN else ""))
NPM = shutil.which("npm") or ("npm.cmd" if WIN else "npm")

PROD = "--prod" in sys.argv or "-p" in sys.argv

_procs = []


def _shutdown(*_):
    for p in _procs:
        try:
            p.terminate()
        except Exception:
            pass
    sys.exit(0)


signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)

if PROD:
    if not os.path.isdir(DIST):
        print("Building frontend…")
        r = subprocess.run([NPM, "run", "build-only"], cwd=FRONTEND_DIR, shell=WIN)
        if r.returncode != 0:
            sys.exit("Frontend build failed.")
    backend = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "src.buyer.api:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=ROOT,
    )
    _procs.append(backend)
    print("\n  App: http://localhost:8000\n")
else:
    backend = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "src.buyer.api:app", "--reload", "--port", "8000"],
        cwd=ROOT,
    )
    _procs.append(backend)
    frontend = subprocess.Popen([NPM, "run", "dev"], cwd=FRONTEND_DIR, shell=WIN)
    _procs.append(frontend)
    print("\n  API:  http://localhost:8000")
    print("  App:  http://localhost:5173\n")

while all(p.poll() is None for p in _procs):
    time.sleep(0.5)

_shutdown()
