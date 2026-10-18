# RFPY
# Copyright © 2026 Olivier RENAULT
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import base64
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer" / "rfpy-installer.ps1"
WEB_HTML = ROOT / "src" / "web" / "web-v1.0.0.html"
WEB_JS = ROOT / "src" / "web" / "web-v1.0.0.js"
RFPY_PY = ROOT / "src" / "rfpy.py"

PAYLOADS = {
    "AppBase64": RFPY_PY,
    "PsBase64": ROOT / "src" / "wrappers" / "rfpy.ps1",
    "CmdBase64": ROOT / "src" / "wrappers" / "rfpy.cmd",
    "UvPsBase64": ROOT / "src" / "wrappers" / "uv.ps1",
    "UvCmdBase64": ROOT / "src" / "wrappers" / "uv.cmd",
    "ConfigBase64": ROOT / "src" / "default-config.json",
    "NoticeBase64": ROOT / "NOTICE",
    "LicenseBase64": ROOT / "LICENSE",
    "AuthorsBase64": ROOT / "AUTHORS",
}


def canonical_payload_bytes(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if path.suffix.lower() in {".ps1", ".cmd"}:
        text = text.replace("\n", "\r\n")
    return text.encode("utf-8")


def installer_payloads() -> dict[str, bytes]:
    text = INSTALLER.read_text(encoding="utf-8-sig")
    result: dict[str, bytes] = {}
    for variable in PAYLOADS:
        match = re.search(rf"(?m)^\${re.escape(variable)}\s*=\s*'([^']*)'$", text)
        if not match:
            raise AssertionError(f"Missing installer payload: {variable}")
        result[variable] = base64.b64decode(match.group(1))
    return result


class ReleaseIntegrityTests(unittest.TestCase):
    def test_external_web_html_matches_rfpy_embedded_web_html_exactly(self):
        spec = importlib.util.spec_from_file_location("rfpy_release_integrity", RFPY_PY)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        embedded = module.WEB_HTML.replace("\r\n", "\n").replace("\r", "\n")
        external = WEB_HTML.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        self.assertEqual(embedded, external, "src/rfpy.py WEB_HTML is stale compared with src/web/web-v1.0.0.html")

    def test_external_javascript_matches_inline_html_script_exactly(self):
        html = WEB_HTML.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        js = WEB_JS.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        self.assertEqual(html.count("<script>"), 1)
        self.assertEqual(html.count("</script>"), 1)
        start = html.index("<script>") + len("<script>")
        end = html.index("</script>", start)
        inline = html[start:end].strip("\n")
        self.assertEqual(inline, js, "Inline JavaScript in web-v1.0.0.html is stale compared with web-v1.0.0.js")

    def test_installer_payloads_match_current_sources_byte_for_byte(self):
        embedded = installer_payloads()
        for variable, source in PAYLOADS.items():
            with self.subTest(payload=variable, source=str(source.relative_to(ROOT))):
                self.assertEqual(
                    embedded[variable],
                    canonical_payload_bytes(source),
                    f"{variable} in installer/rfpy-installer.ps1 is stale; run python tools/embed_payloads.py",
                )

    def test_web_inline_handlers_have_javascript_function_definitions(self):
        html = WEB_HTML.read_text(encoding="utf-8")
        js = WEB_JS.read_text(encoding="utf-8")
        handlers = set(
            re.findall(
                r'on(?:click|change|dblclick|input|keyup|keydown|submit)="\s*([A-Za-z_$][\w$]*)\s*\(',
                html,
            )
        )
        handlers.discard("$")
        missing = sorted(
            name
            for name in handlers
            if not re.search(rf"\b(?:async\s+)?function\s+{re.escape(name)}\s*\(", js)
        )
        self.assertEqual(missing, [], f"HTML references undefined JavaScript handlers: {missing}")

    def test_env_type_regression_functions_exist_in_every_packaging_layer(self):
        required = ("function currentEnvType()", "function envTypeChanged()")
        external_js = WEB_JS.read_text(encoding="utf-8")
        external_html = WEB_HTML.read_text(encoding="utf-8")
        rfpy_source = RFPY_PY.read_text(encoding="utf-8")
        app_payload = installer_payloads()["AppBase64"].decode("utf-8-sig")
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, external_js)
                self.assertIn(marker, external_html)
                self.assertIn(marker, rfpy_source)
                self.assertIn(marker, app_payload)

    def test_embed_payloads_repairs_stale_web_layers_before_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp) / "RFPY"
            for rel in ("installer", "src", "tools"):
                shutil.copytree(ROOT / rel, temp_root / rel)
            for name in ("NOTICE", "LICENSE", "AUTHORS"):
                shutil.copy2(ROOT / name, temp_root / name)

            app = temp_root / "src" / "rfpy.py"
            app_text = app.read_text(encoding="utf-8")
            app.write_text(app_text.replace("function envTypeChanged()", "function envTypeChanged_STALE()", 1), encoding="utf-8")

            subprocess.run(
                [sys.executable, str(temp_root / "tools" / "embed_payloads.py")],
                cwd=temp_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            repaired = app.read_text(encoding="utf-8")
            self.assertIn("function envTypeChanged()", repaired)
            self.assertNotIn("function envTypeChanged_STALE()", repaired)

            installer = (temp_root / "installer" / "rfpy-installer.ps1").read_text(encoding="utf-8-sig")
            match = re.search(r"(?m)^\$AppBase64\s*=\s*'([^']*)'$", installer)
            self.assertIsNotNone(match)
            payload = base64.b64decode(match.group(1)).decode("utf-8-sig")
            self.assertIn("function envTypeChanged()", payload)
            self.assertNotIn("function envTypeChanged_STALE()", payload)

    def test_embed_payloads_is_idempotent_on_a_clean_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp) / "RFPY"
            for rel in (
                "installer",
                "src",
                "tools",
            ):
                shutil.copytree(ROOT / rel, temp_root / rel)
            for name in ("NOTICE", "LICENSE", "AUTHORS"):
                shutil.copy2(ROOT / name, temp_root / name)

            installer = temp_root / "installer" / "rfpy-installer.ps1"
            before = installer.read_bytes()
            subprocess.run(
                [sys.executable, str(temp_root / "tools" / "embed_payloads.py")],
                cwd=temp_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            after_first = installer.read_bytes()
            subprocess.run(
                [sys.executable, str(temp_root / "tools" / "embed_payloads.py")],
                cwd=temp_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            after_second = installer.read_bytes()
            self.assertEqual(before, after_first, "Installer payloads were stale before the test")
            self.assertEqual(after_first, after_second, "embed_payloads.py is not idempotent")


if __name__ == "__main__":
    unittest.main()
