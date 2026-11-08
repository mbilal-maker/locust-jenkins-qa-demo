"""Start the demo API, run Locust headlessly and cleanly stop the API."""
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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_api(base, proc, timeout=25):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"API exited during startup: {proc.returncode}")
        try:
            with urlopen(base + "/health", timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, OSError, TimeoutError):
            pass
        time.sleep(0.3)
    raise RuntimeError("API did not become healthy")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=PROFILES, default="smoke")
    args = parser.parse_args()
    REPORTS.mkdir(parents=True, exist_ok=True)
    users, spawn_rate, duration = PROFILES[args.profile]
    port = free_port()
    host = f"http://127.0.0.1:{port}"
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    print(f"Starting {args.profile}: {users} users, {spawn_rate}/sec, {duration}", flush=True)

    with (REPORTS / "staging-api.log").open("w", encoding="utf-8") as api_log:
        api = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT, env=env, stdout=api_log, stderr=subprocess.STDOUT,
        )
        try:
            wait_for_api(host, api)
            command = [
                sys.executable, "-m", "locust", "-f", "locustfile.py",
                "--headless", "--host", host,
                "--users", str(users), "--spawn-rate", str(spawn_rate),
                "--run-time", duration, "--stop-timeout", "5",
                "--html", "reports/locust-report.html",
                "--csv", "reports/locust",
            ]
            result = subprocess.run(command, cwd=ROOT, env=env, check=False)
            print(f"Locust exit code: {result.returncode}", flush=True)
            return result.returncode
        finally:
            if api.poll() is None:
                api.terminate()
                try:
                    api.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    api.kill()
                    api.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
