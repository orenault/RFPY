# RFPY
# Copyright © 2026 Olivier RENAULT
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
WEB_DIR = SRC_DIR / "web"
WRAPPERS_DIR = SRC_DIR / "wrappers"
INSTALLER = ROOT / "installer" / "rfpy-installer.ps1"
WEB_HTML_FILE = WEB_DIR / "web-v1.0.0.html"
WEB_JS_FILE = WEB_DIR / "web-v1.0.0.js"
APP_FILE = SRC_DIR / "rfpy.py"

PAYLOADS = {
    "AppBase64": APP_FILE,
    "PsBase64": WRAPPERS_DIR / "rfpy.ps1",
    "CmdBase64": WRAPPERS_DIR / "rfpy.cmd",
    "WebPsBase64": WRAPPERS_DIR / "rfpyw.ps1",
    "WebCmdBase64": WRAPPERS_DIR / "rfpyw.cmd",
    "UvPsBase64": WRAPPERS_DIR / "uv.ps1",
    "UvCmdBase64": WRAPPERS_DIR / "uv.cmd",
    "ConfigBase64": SRC_DIR / "default-config.json",
    "NoticeBase64": ROOT / "NOTICE",
    "LicenseBase64": ROOT / "LICENSE",
    "AuthorsBase64": ROOT / "AUTHORS",
}


def normalized_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def sync_web_sources() -> None:
    """Keep the three Web packaging layers identical and deterministic.

    Source of truth for JavaScript: src/web/web-v1.0.0.js
    Source of truth for HTML/CSS structure: src/web/web-v1.0.0.html
    Runtime copy: WEB_HTML raw string inside src/rfpy.py
    """
    js = normalized_text(WEB_JS_FILE)
    html = normalized_text(WEB_HTML_FILE)

    if html.count("<script>") != 1 or html.count("</script>") != 1:
        raise SystemExit("web-v1.0.0.html must contain exactly one inline <script> block")

    script_open = html.index("<script>") + len("<script>")
    script_close = html.index("</script>", script_open)
    html = html[:script_open] + "\n" + js + "\n" + html[script_close:]
    WEB_HTML_FILE.write_text(html, encoding="utf-8", newline="\n")

    if "'''" in html:
        raise SystemExit("web-v1.0.0.html contains triple single quotes and cannot be embedded safely")

    app = normalized_text(APP_FILE)
    marker = "WEB_HTML = r'''"
    start = app.find(marker)
    if start < 0:
        raise SystemExit("WEB_HTML raw string not found in src/rfpy.py")
    content_start = start + len(marker)
    content_end = app.find("'''", content_start)
    if content_end < 0:
        raise SystemExit("WEB_HTML raw string terminator not found in src/rfpy.py")

    app = app[:content_start] + html + app[content_end:]
    APP_FILE.write_text(app, encoding="utf-8", newline="\n")


def canonical_payload_bytes(path: Path) -> bytes:
    """Return deterministic payload bytes independently of checkout line endings."""
    text = normalized_text(path)

    # Runtime PowerShell/CMD wrappers are Windows files.
    if path.suffix.lower() in {".ps1", ".cmd"}:
        text = text.replace("\n", "\r\n")

    return text.encode("utf-8")


def refresh_installer_payloads() -> None:
    sync_web_sources()

    text = normalized_text(INSTALLER)
    for variable, source in PAYLOADS.items():
        encoded = base64.b64encode(canonical_payload_bytes(source)).decode("ascii")
        pattern = rf"(?m)^\${re.escape(variable)}\s*=\s*'[^']*'$"
        text, count = re.subn(pattern, f"${variable} = '{encoded}'", text, count=1)
        if count != 1:
            raise SystemExit(f"Payload variable not found exactly once: {variable}")

    # The installer itself is a Windows PowerShell source file.
    INSTALLER.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))


if __name__ == "__main__":
    refresh_installer_payloads()
    print("Web sources synchronized and installer payloads refreshed")
