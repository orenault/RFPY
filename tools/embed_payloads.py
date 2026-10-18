# RFPY
# Copyright © 2026 Olivier RENAULT
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "rfpy-installer.ps1"
PAYLOADS = {
    "AppBase64": ROOT / "rfpy.py",
    "PsBase64": ROOT / "rfpy.ps1",
    "CmdBase64": ROOT / "rfpy.cmd",
    "UvPsBase64": ROOT / "uv.ps1",
    "UvCmdBase64": ROOT / "uv.cmd",
    "ConfigBase64": ROOT / "default-config.json",
    "NoticeBase64": ROOT / "NOTICE",
    "LicenseBase64": ROOT / "LICENSE",
    "AuthorsBase64": ROOT / "AUTHORS",
}

text = INSTALLER.read_text(encoding="utf-8")
for variable, source in PAYLOADS.items():
    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    pattern = rf"(?m)^\${re.escape(variable)}\s*=\s*'[^']*'$"
    text, count = re.subn(pattern, f"${variable} = '{encoded}'", text, count=1)
    if count != 1:
        raise SystemExit(f"Payload variable not found exactly once: {variable}")
INSTALLER.write_text(text, encoding="utf-8")
print("Embedded payloads refreshed in rfpy-installer.ps1")
