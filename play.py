"""Pokreće Django server i Cloudflare tunnel jednom naredbom.

Upotreba:      python play.py
Zaustavljanje: Ctrl+C (gasi oboje)
"""
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from collections import deque
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PORT = 8000
URL_PATTERN = re.compile(r"https://([a-z0-9-]+)\.trycloudflare\.com")


def find_cloudflared():
    found = shutil.which("cloudflared")
    if found:
        return found
    # Na Windowsu PATH u terminalu zna biti zastario, pa gledamo i uobičajena mjesta.
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "cloudflared" / "cloudflared.exe",
        Path(os.environ.get("ProgramFiles", "")) / "cloudflared" / "cloudflared.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "cloudflared.exe",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def copy_to_clipboard(text):
    command = {"win32": ["clip"], "darwin": ["pbcopy"]}.get(sys.platform)
    if command is None:
        return False
    try:
        subprocess.run(command, input=text, text=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def announce(url):
    copied = copy_to_clipboard(url)
    bar = "=" * 64
    print(f"\n{bar}\n  Puzzle Party is live at:\n\n  {url}\n")
    if copied:
        print("  (link je kopiran u clipboard)")
    print(f"{bar}\n", flush=True)
    webbrowser.open(url)


def watch_tunnel(process, recent):
    url = None
    announced = False
    for line in process.stdout:
        recent.append(line.rstrip())
        match = URL_PATTERN.search(line)
        # "api.trycloudflare.com" se pojavljuje u porukama o greškama, to nije naš link.
        if url is None and match and match.group(1) != "api":
            url = match.group(0)
        # Link stvarno radi tek kad se tunnel spoji na Cloudflare.
        if url and not announced and "Registered tunnel connection" in line:
            announced = True
            announce(url)


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def main():
    cloudflared = find_cloudflared()
    if cloudflared is None:
        print("cloudflared nije pronađen. Instaliraj ga s:")
        print("  winget install --id Cloudflare.cloudflared")
        return 1

    # sys.executable = Python iz .venv-a kojim je pokrenuta ova skripta.
    server = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"127.0.0.1:{PORT}", "--noreload"],
        cwd=BASE_DIR,
    )
    tunnel = subprocess.Popen(
        [cloudflared, "tunnel", "--url", f"http://127.0.0.1:{PORT}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    recent = deque(maxlen=15)
    threading.Thread(target=watch_tunnel, args=(tunnel, recent), daemon=True).start()
    print("Starting server and tunnel... (Ctrl+C to stop)", flush=True)

    try:
        while server.poll() is None and tunnel.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
    else:
        if tunnel.poll() is not None:
            print("\nTunnel stopped unexpectedly. Last cloudflared output:")
            print("\n".join(recent))
        else:
            print("\nServer stopped. See the error above.")
    finally:
        stop(server)
        stop(tunnel)
    return 0


if __name__ == "__main__":
    sys.exit(main())