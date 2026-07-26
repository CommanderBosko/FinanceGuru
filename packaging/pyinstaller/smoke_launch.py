"""Launch a frozen build, keep it alive under a timeout, and report success.

Mirrors the flake.nix qt-launch check / flatpak-check CI step's philosophy
(process must stay running when killed, not exit early) without depending on
GNU timeout/xvfb-run, which aren't present on Windows runners.
"""

import argparse
import os
import subprocess
import sys
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable")
    parser.add_argument("--seconds", type=float, default=5.0)
    args = parser.parse_args()

    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    proc = subprocess.Popen([args.executable], env=env)
    time.sleep(args.seconds)
    still_running = proc.poll() is None
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    if not still_running:
        sys.exit(
            f"{args.executable} exited early (code {proc.returncode}) "
            "instead of staying up under the timeout"
        )
    print("Launch smoke check passed: process stayed alive under the timeout.")


if __name__ == "__main__":
    main()
