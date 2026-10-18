# RFPY
# Copyright © 2026 Olivier RENAULT
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
WRAPPERS_DIR = SRC_DIR / "wrappers"
INSTALLER = ROOT / "installer" / "rfpy-installer.ps1"

PAYLOADS = {
    "AppBase64": SRC_DIR / "rfpy.py",
    "PsBase64": WRAPPERS_DIR / "rfpy.ps1",
    "CmdBase64": WRAPPERS_DIR / "rfpy.cmd",
    "UvPsBase64": WRAPPERS_DIR / "uv.ps1",
    "UvCmdBase64": WRAPPERS_DIR / "uv.cmd",
    "ConfigBase64": SRC_DIR / "default-config.json",
    "NoticeBase64": ROOT / "NOTICE",
    "LicenseBase64": ROOT / "LICENSE",
    "AuthorsBase64": ROOT / "AUTHORS",
}


def canonical_payload_bytes(path: Path) -> bytes:
    """Return deterministic payload bytes independently of checkout line endings."""
    text = path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Runtime PowerShell/CMD wrappers are Windows files.
    if path.suffix.lower() in {".ps1", ".cmd"}:
        text = text.replace("\n", "\r\n")

    return text.encode("utf-8")


text = INSTALLER.read_text(encoding="utf-8")
text = text.replace("\r\n", "\n").replace("\r", "\n")

for variable, source in PAYLOADS.items():
    encoded = base64.b64encode(canonical_payload_bytes(source)).decode("ascii")
    pattern = rf"(?m)^\${re.escape(variable)}\s*=\s*'[^']*'$"
    text, count = re.subn(pattern, f"${variable} = '{encoded}'", text, count=1)
    if count != 1:
        raise SystemExit(f"Payload variable not found exactly once: {variable}")

# The installer itself is a Windows PowerShell source file.
INSTALLER.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
print("Embedded payloads refreshed in installer/rfpy-installer.ps1")
