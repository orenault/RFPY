# RFPY
# Copyright © 2026 Olivier RENAULT
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
import venv as venv_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / 'src' / 'wrappers' / 'rfpy.ps1'
CMD = ROOT / 'src' / 'wrappers' / 'rfpy.cmd'


class CliPromptAndWebHotkeyTests(unittest.TestCase):
    def test_f3_web_hotkey_is_available_in_cli_and_localized(self):
        ps1 = PS1.read_text(encoding='utf-8-sig')
        self.assertIn("[ConsoleKey]::F3", ps1)
        self.assertIn("RfpySpecial='web'", ps1)
        self.assertIn("function Test-WebSpecial", ps1)
        self.assertIn("-EnableWebHotkey", ps1)
        self.assertIn("Call-RfpyCore @('web')", ps1)
        for label in (
            "f3='F3 : Web'",
            "f3='F3: Web'",
            "f3='F3：Web'",
        ):
            self.assertIn(label, ps1)

    def test_cmd_prompt_prefix_is_set_and_restored(self):
        cmd = CMD.read_text(encoding='utf-8-sig')
        self.assertIn('RFPY_ORIGINAL_PROMPT', cmd)
        self.assertIn('RFPY_PROMPT_SAVED', cmd)
        self.assertIn('set "PROMPT=[RFPY - %RFPY_SELECTED%] %RFPY_ORIGINAL_PROMPT%"', cmd)
        self.assertIn('set "PROMPT=%RFPY_ORIGINAL_PROMPT%"', cmd)

    @unittest.skipUnless(os.name == 'nt', 'CMD prompt integration test requires Windows')
    def test_cmd_activation_prefixes_prompt_and_off_restores_it(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'RFPY'
            (root / 'bin').mkdir(parents=True)
            (root / 'app').mkdir(parents=True)
            (root / '.appvenv' / 'Scripts').mkdir(parents=True)
            demo_venv = root / 'stacks' / 'demo' / '.venv'
            (demo_venv / 'Scripts').mkdir(parents=True)

            venv_module.EnvBuilder(with_pip=False, clear=True).create(root / '.appvenv')
            (demo_venv / 'Scripts' / 'python.exe').write_bytes(b'')
            shutil.copy2(CMD, root / 'bin' / 'rfpy.cmd')
            (root / 'bin' / 'rfpy.ps1').write_text(
                'param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)\nexit 0\n',
                encoding='utf-8-sig',
            )
            (root / 'app' / 'rfpy.py').write_text(
                'import sys\n'
                'if len(sys.argv)>1 and sys.argv[1]=="env-shell-tsv":\n'
                f'    print(r"{demo_venv}|shared|")\n'
                '    raise SystemExit(0)\n'
                'raise SystemExit(0)\n',
                encoding='utf-8',
            )

            driver = Path(td) / 'driver.cmd'
            driver.write_text(
                '@echo off\r\n'
                'set "PROMPT=BASE:$P$G"\r\n'
                f'call "{root / "bin" / "rfpy.cmd"}" activate demo >nul 2>&1\r\n'
                'echo __ACTIVATE_RC__=%ERRORLEVEL%\r\n'
                'echo __ACTIVE_PROMPT__=%PROMPT%\r\n'
                f'call "{root / "bin" / "rfpy.cmd"}" off >nul 2>&1\r\n'
                'echo __OFF_RC__=%ERRORLEVEL%\r\n'
                'echo __RESTORED_PROMPT__=%PROMPT%\r\n',
                encoding='utf-8',
            )
            cp = subprocess.run(
                ['cmd.exe', '/d', '/u', '/c', str(driver)],
                text=False,
                capture_output=True,
                timeout=20,
            )
            stdout = (cp.stdout or b'').decode('utf-16-le', errors='strict')
            stderr = (cp.stderr or b'').decode('utf-16-le', errors='replace')
            output = stdout + stderr
            self.assertEqual(cp.returncode, 0, output)
            self.assertIn('__ACTIVATE_RC__=0', stdout)
            self.assertIn('__ACTIVE_PROMPT__=[RFPY - demo] BASE:$P$G', stdout)
            self.assertIn('__OFF_RC__=0', stdout)
            self.assertIn('__RESTORED_PROMPT__=BASE:$P$G', stdout)


if __name__ == '__main__':
    unittest.main()
