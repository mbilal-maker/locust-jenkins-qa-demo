"""One-process runner for Windows Jenkins: staging API + Locust + cleanup.
Run: python scripts/run_ci.py --profile smoke
"""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
PROFILES = {
    "smoke": (10, 5, "30s"),
    "load": (30, 5, "60s"),
    "stress": (60, 10, "90s"),
}


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        return server.getsockname()[1]


def wait_until_ready(url, proc, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if proc.poll() is not None:
            raise RuntimeError(f"API exited during startup; exit code={proc.returncode}")
        try:
            with urlopen(url + "/health", timeout=1) as result:
                if result.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(.3)
    raise RuntimeError("Staging API failed health check within 20 seconds")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=PROFILES, default="smoke")
    args = parser.parse_args()
    REPORTS.mkdir(exist_ok=True)
    users, spawn_rate, duration = PROFILES[args.profile]
    port = free_port()
    host = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    print(f"[QA] Profile={args.profile}, users={users}, spawn-rate={spawn_rate}/s, duration={duration}", flush=True)
    api_log = open(REPORTS / "staging-api.log", "w", encoding="utf-8")
    api = None
    try:
        api = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=str(ROOT), env=env, stdout=api_log, stderr=subprocess.STDOUT,
        )
        wait_until_ready(host, api)
        print(f"[QA] Staging API ready at {host}", flush=True)
        cmd = [
            sys.executable, "-m", "locust", "-f", "locustfile.py", "--headless",
            "--host", host, "--users", str(users), "--spawn-rate", str(spawn_rate),
            "--run-time", duration, "--stop-timeout", "5",
            "--html", "reports/locust-report.html", "--csv", "reports/locust",
        ]
        result = subprocess.run(cmd, cwd=str(ROOT), env=env, check=False)
        print(f"[QA] Locust exit code: {result.returncode}", flush=True)
        return result.returncode
    finally:
        if api is not None and api.poll() is None:
            api.terminate()
            try:
                api.wait(timeout=8)
            except subprocess.TimeoutExpired:
                api.kill()
                api.wait(timeout=5)
        api_log.close()


if __name__ == "__main__":
    sys.exit(main())
