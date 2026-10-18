# RFPY
# Copyright © 2026 Olivier RENAULT
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv as venv_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / 'src' / 'web' / 'web-v1.0.0.html'
JS = ROOT / 'src' / 'web' / 'web-v1.0.0.js'
CMD = ROOT / 'src' / 'wrappers' / 'rfpy.cmd'


class SettingsAndCmdRegressionTests(unittest.TestCase):
    def test_settings_and_repositories_are_one_card_with_save_at_top(self):
        html = HTML.read_text(encoding='utf-8')
        self.assertEqual(html.count('id="repoCard"'), 1)
        self.assertIn('id="settingsSaveTop"', html)
        self.assertIn('id="publicPyPISection"', html)
        self.assertIn('id="privateRepositoriesSection"', html)
        self.assertIn('id="pypiRepo"', html)
        self.assertIn('id="privateReposList"', html)
        self.assertLess(html.index('id="settingsSaveTop"'), html.index('data-i="defaults"'))

    def test_settings_rows_have_localized_help_and_dirty_guard(self):
        js = JS.read_text(encoding='utf-8')
        html = HTML.read_text(encoding='utf-8')
        for key in (
            'publicPyPIHelp', 'privateRepositoriesHelp', 'proxySectionHelp',
            'caSectionHelp', 'webPortSectionHelp', 'installSafetyHelp',
            'versionFiltersHelp', 'defaultsHelp', 'unsavedSettingsQuit',
        ):
            self.assertIn(key, js)
        self.assertIn('id="settingsDirty"', html)
        self.assertIn('settingsDirty()', js)
        self.assertIn("window.addEventListener('beforeunload'", js)

    def test_enabled_repository_requires_simple_url_and_http_scheme(self):
        js = JS.read_text(encoding='utf-8')
        self.assertIn("if(r.enabled&&!r.simple_url)", js)
        self.assertIn("isHttpUrl(r.simple_url)", js)
        self.assertIn("enabledRepoNeedsUrl", js)
        self.assertIn("invalidRepoUrl", js)
        self.assertIn("enabled:false", js, 'New private repositories must start disabled')

    def test_multiple_private_repositories_are_supported(self):
        js = JS.read_text(encoding='utf-8')
        self.assertIn("privateRows.map(repoRowData)", js)
        self.assertNotIn('onlyOnePrivateRepo', js)

    def test_cmd_activation_message_runs_before_endlocal(self):
        cmd = CMD.read_text(encoding='utf-8-sig')
        start = cmd.index('\n:activate_selected\n')
        end = cmd.index('\n:deactivate\n', start)
        section = cmd[start:end]
        call = section.index('cmd-activated')
        endlocal = section.index('endlocal & (')
        self.assertLess(call, endlocal, 'RFPY_PS must be used before endlocal destroys local variables')
        self.assertNotIn('-File "%RFPY_PS%" cmd-activated "%RFPY_ENV%"', section[endlocal:])

    @unittest.skipUnless(os.name == 'nt', 'CMD environment persistence test requires Windows')
    def test_cmd_activate_persists_environment_in_parent_cmd(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'RFPY'
            (root / 'bin').mkdir(parents=True)
            (root / 'app').mkdir(parents=True)
            (root / '.appvenv' / 'Scripts').mkdir(parents=True)
            venv = root / 'stacks' / 'demo' / '.venv'
            (venv / 'Scripts').mkdir(parents=True)

            venv_module.EnvBuilder(with_pip=False, clear=True).create(root / '.appvenv')
            # The selected environment Python only needs to exist for wrapper validation.
            (venv / 'Scripts' / 'python.exe').write_bytes(b'')
            shutil.copy2(CMD, root / 'bin' / 'rfpy.cmd')
            (root / 'bin' / 'rfpy.ps1').write_text(
                'param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)\nexit 0\n',
                encoding='utf-8-sig',
            )
            (root / 'app' / 'rfpy.py').write_text(
                'import sys\n'
                'if len(sys.argv)>1 and sys.argv[1]=="env-shell-tsv":\n'
                f'    print(r"{venv}|shared|")\n'
                '    raise SystemExit(0)\n'
                'raise SystemExit(0)\n',
                encoding='utf-8',
            )

            driver = Path(td) / 'driver.cmd'
            driver.write_text(
                '@echo off\r\n'
                f'call "{root / "bin" / "rfpy.cmd"}" activate demo >nul 2>&1\r\n'
                'echo __RC__=%ERRORLEVEL%\r\n'
                'echo __ENV__=%RFPY_ENV%\r\n'
                'echo __VENV__=%VIRTUAL_ENV%\r\n',
                encoding='utf-8',
            )
            # /u makes CMD built-in output deterministic UTF-16LE when redirected.
            # The wrapper output itself is suppressed here: this integration test
            # validates persistence in the *parent CMD environment*, not console encoding.
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
            self.assertIn('__RC__=0', stdout)
            self.assertIn('__ENV__=demo', stdout)
            self.assertIn(f'__VENV__={venv}', stdout)
            self.assertNotIn('Le chemin d\'accès n\'a pas une forme conforme', output)
            self.assertNotIn('The path is not of a legal form', output)


if __name__ == '__main__':
    unittest.main()
