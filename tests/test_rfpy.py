# RFPY tests
# Copyright © 2026 Olivier RENAULT
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


class RfpyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ['RFPY_HOME'] = cls.tmp.name
        src = Path(__file__).resolve().parents[1] / 'rfpy.py'
        spec = importlib.util.spec_from_file_location('rfpy_test_module', src)
        cls.rfpy = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(cls.rfpy)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_default_config_is_created(self):
        cfg = self.rfpy.load_config()
        self.assertTrue(self.rfpy.CONFIG_FILE.exists())
        self.assertTrue(cfg['artifact']['enabled'])
        self.assertEqual(cfg['repositories'][0]['type'], 'pypi')
        self.assertEqual(cfg['defaults']['python'], '')
        self.assertEqual(cfg['defaults']['robot'], '')

    def test_name_validation(self):
        self.assertEqual(self.rfpy.normalize_name('Demo-314'), 'Demo-314')
        with self.assertRaises(self.rfpy.RfpyError):
            self.rfpy.normalize_name('bad/name')

    def test_deep_merge_preserves_defaults(self):
        merged = self.rfpy.deep_merge({'a': {'b': 1, 'c': 2}}, {'a': {'b': 9}})
        self.assertEqual(merged, {'a': {'b': 9, 'c': 2}})


    def test_concise_python_versions_one_per_branch_and_rc_fallback(self):
        original = self.rfpy.stable_versions_from_uv
        try:
            self.rfpy.stable_versions_from_uv = lambda request=None: [
                '3.15.0rc3', '3.15.0rc2',
                '3.14.8', '3.14.7', '3.14.8rc1',
                '3.13.15', '3.13.14',
                '3.16.0b1',
            ]
            out = self.rfpy.concise_python_versions()
            self.assertEqual(out[0], {'branch': '3.15', 'version': '3.15.0rc3', 'kind': 'rc'})
            self.assertEqual(out[1], {'branch': '3.14', 'version': '3.14.8', 'kind': 'stable'})
            self.assertEqual(out[2], {'branch': '3.13', 'version': '3.13.15', 'kind': 'stable'})
            self.assertFalse(any(x['branch'] == '3.16' for x in out))
        finally:
            self.rfpy.stable_versions_from_uv = original

    def test_concise_robot_versions_one_per_branch(self):
        original = self.rfpy.robot_versions
        try:
            self.rfpy.robot_versions = lambda: ['7.4.2','7.4.1','7.3.2','6.1.1']
            out = self.rfpy.concise_robot_versions()
            self.assertEqual(out[0], {'branch':'7.4','version':'7.4.2'})
            self.assertEqual(out[1], {'branch':'7.3','version':'7.3.2'})
        finally:
            self.rfpy.robot_versions = original

    def test_default_package_sets_exist(self):
        cfg = self.rfpy.load_config()
        self.assertIn('RF Web - Playwright', cfg['package_sets'])
        self.assertIn('RF API', cfg['package_sets'])

    def test_web_has_five_languages_and_custom_version_choices(self):
        html = self.rfpy.WEB_HTML
        for code in ('fr','en','de','es','zh'):
            self.assertIn(f"setLang('{code}')", html)
        self.assertNotIn('select id="lang"', html)
        self.assertIn('class="globe"', html)
        self.assertIn('__custom__', html)
        self.assertIn('/api/packages/install', html)

    def test_rename_relocatable_environment(self):
        old = self.rfpy.STACKS_DIR / 'old'
        venv = old / '.venv'
        scripts = venv / ('Scripts' if os.name == 'nt' else 'bin')
        scripts.mkdir(parents=True, exist_ok=True)
        py = scripts / ('python.exe' if os.name == 'nt' else 'python')
        py.write_text('', encoding='ascii')
        (venv / 'pyvenv.cfg').write_text('relocatable = true\n', encoding='ascii')
        manifest = {'name': 'old', 'venv': str(venv), 'stack_dir': str(old), 'profile': 'python'}
        (old / 'rfpy.json').write_text(json.dumps(manifest), encoding='utf-8')
        out = self.rfpy.rename_environment('old', 'new')
        self.assertEqual(out['name'], 'new')
        self.assertTrue((self.rfpy.STACKS_DIR / 'new' / 'rfpy.json').exists())


    def test_environment_type_aliases(self):
        self.assertEqual(self.rfpy.normalize_environment_type('project'), 'project')
        self.assertEqual(self.rfpy.normalize_environment_type('Projet'), 'project')
        self.assertEqual(self.rfpy.normalize_environment_type('shared'), 'shared')
        self.assertEqual(self.rfpy.normalize_environment_type('global'), 'shared')
        with self.assertRaises(self.rfpy.RfpyError):
            self.rfpy.normalize_environment_type('other')

    def test_project_probe(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / 'pyproject.toml').write_text('[project]\nname="x"\nversion="0"\n', encoding='utf-8')
            d = self.rfpy.probe_project(str(p))
            self.assertTrue(d['exists'])
            self.assertTrue(d['pyproject'])
            self.assertFalse(d['uv_lock'])

    def test_old_manifest_defaults_to_shared(self):
        old = self.rfpy.STACKS_DIR / 'legacy'
        venv = old / '.venv'
        scripts = venv / ('Scripts' if os.name == 'nt' else 'bin')
        scripts.mkdir(parents=True, exist_ok=True)
        py = scripts / ('python.exe' if os.name == 'nt' else 'python')
        py.write_text('', encoding='ascii')
        (old / 'rfpy.json').write_text(json.dumps({'name':'legacy','venv':str(venv),'profile':'python'}), encoding='utf-8')
        items = [x for x in self.rfpy.list_envs() if x['name']=='legacy']
        self.assertEqual(items[0]['environment_type'], 'shared')

    def test_backend_no_args_opens_web_on_first_run(self):
        original_list = self.rfpy.list_envs
        original_web = self.rfpy.serve_web
        called = []
        try:
            self.rfpy.list_envs = lambda *a, **k: []
            self.rfpy.serve_web = lambda *a, **k: called.append(True)
            self.assertEqual(self.rfpy.main([]), 0)
            self.assertEqual(called, [True])
        finally:
            self.rfpy.list_envs = original_list
            self.rfpy.serve_web = original_web

    def test_backend_empty_install_opens_web_failsafe(self):
        root = Path(__file__).resolve().parents[1]
        app = (root / "rfpy.py").read_text(encoding="utf-8")
        self.assertIn("Aucun environnement n existe encore. Ouverture de la console Web", app)
        self.assertIn("serve_web()", app)

    def test_shell_defaults_to_on_and_scans_stacks_directly(self):
        root = Path(__file__).resolve().parents[1]
        ps = (root / 'rfpy.ps1').read_text(encoding='utf-8')
        self.assertIn("[Parameter(Position=0)][string]$Action = 'on'", ps)
        self.assertIn('function Find-ManagedEnvironments', ps)
        self.assertIn('Get-ChildItem -LiteralPath $RfpyStacks', ps)
        self.assertIn('Open-FirstRun', ps)
        self.assertIn('$env:Path = "$RfpyBin;$scripts;$base"', ps)

    def test_installer_returns_to_path_only_model(self):
        root = Path(__file__).resolve().parents[1]
        installer = (root / 'rfpy-installer.ps1').read_text(encoding='utf-8')
        self.assertIn('Remove-RfpyOldProfileShims', installer)
        self.assertIn('Ensure-UserPath $BinDir', installer)


    def test_shell_manifest_access_is_tolerant(self):
        root = Path(__file__).resolve().parents[1]
        ps = (root / "rfpy.ps1").read_text(encoding="utf-8")
        self.assertIn("function Read-ManifestField", ps)
        self.assertIn("'robot_resolved','robot_requested','robot_version','robot'", ps)
        self.assertIn("'python_resolved','python_requested','python_version','python'", ps)
        self.assertNotIn("elseif ($m.robot_version)", ps)
        self.assertNotIn("elseif ($m.python_version)", ps)

    def test_web_230_features(self):
        html = self.rfpy.WEB_HTML
        for token in ('/api/fs/roots','/api/project-path','/api/duplicate','/api/open-file','testHeadless','installationProfile','recentPython','recentRobot'):
            self.assertIn(token, html)
        self.assertNotIn('pipFreeze', html)
        self.assertNotIn('Python stdlib', html)
        self.assertIn('data:image/webp;base64,', html)

    def test_config_230_profiles_language_and_filters(self):
        cfg = self.rfpy.load_config()
        self.assertIn('installation_profiles', cfg)
        self.assertIn('RF Web - Playwright', cfg['installation_profiles'])
        self.assertEqual(cfg['ui']['language'], 'fr')
        self.assertTrue(cfg['version_filters']['python_recent_only'])
        self.assertTrue(cfg['version_filters']['robot_recent_only'])

    def test_project_folder_uniqueness_helper(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / 'project'
            env = self.rfpy.STACKS_DIR / 'unique-env'
            venv = env / '.venv'
            scripts = venv / ('Scripts' if os.name == 'nt' else 'bin')
            scripts.mkdir(parents=True, exist_ok=True)
            (scripts / ('python.exe' if os.name == 'nt' else 'python')).write_text('', encoding='ascii')
            (env / 'rfpy.json').write_text(json.dumps({'name':'unique-env','venv':str(venv),'environment_type':'project','project_path':str(project)}), encoding='utf-8')
            self.assertEqual(self.rfpy.project_path_owner(str(project)), 'unique-env')
            with self.assertRaises(self.rfpy.RfpyError):
                self.rfpy.assert_project_path_available(str(project))

    def test_shell_menu_uses_keyboard_actions_and_language_config(self):
        root = Path(__file__).resolve().parents[1]
        ps = (root / 'rfpy.ps1').read_text(encoding='utf-8')
        self.assertIn('function Pick-FromList', ps)
        self.assertIn("$language = 'fr'", ps)
        self.assertIn("$rawCfg.ui.PSObject.Properties['language']", ps)
        self.assertNotIn("Read-Host 'Action [1-4]'", ps)
        self.assertIn("'project-pending'", ps)


    def test_project_without_folder_is_project_pending(self):
        root = Path(__file__).resolve().parents[1]
        app = (root / 'rfpy.py').read_text(encoding='utf-8')
        self.assertIn('("project" if project else "project-pending") if env_type == "project" else "active-venv"', app)

    def test_web_branding_profiles_and_graphical_controls(self):
        html = self.rfpy.WEB_HTML
        self.assertIn('data:image/webp;base64,', html)
        self.assertIn('class="globe"', html)
        self.assertIn('toggleLangMenu()', html)
        self.assertNotIn('select id="lang"', html)
        self.assertIn('pickInstallProject()', html)
        self.assertIn('profileMode', html)
        self.assertIn('deleteInstallProfile()', html)
        self.assertIn('testHeadless', html)
        self.assertNotIn('pipFreeze', html)

    def test_profile_install_runs_browser_runtime_when_needed(self):
        root = Path(__file__).resolve().parents[1]
        app = (root / 'rfpy.py').read_text(encoding='utf-8')
        self.assertIn('def post_install_package_runtime', app)
        self.assertIn('[str(rfbrowser),"install","chromium"]', app.replace(' ',''))


    def test_installer_preserves_multilingual_powershell_utf8(self):
        root = Path(__file__).resolve().parents[1]
        installer = (root / "rfpy-installer.ps1").read_text(encoding="utf-8")
        shell = (root / "rfpy.ps1").read_text(encoding="utf-8")
        self.assertIn("[IO.File]::ReadAllText($rfpyPsPath, $utf8NoBom)", installer)
        self.assertIn("[Text.UTF8Encoding]::new($true)", installer)
        self.assertIn("UTF-8 BOM valide", installer)
        self.assertIn("正在打开 Web 控制台", shell)
        self.assertNotIn("æ­£åœ¨", shell)


    def _make_fake_env(self, name, env_type="shared", project_path=""):
        env = self.rfpy.STACKS_DIR / name
        venv = env / ".venv"
        scripts = venv / ("Scripts" if os.name == "nt" else "bin")
        scripts.mkdir(parents=True, exist_ok=True)
        py = scripts / ("python.exe" if os.name == "nt" else "python")
        py.write_text("", encoding="ascii")
        (venv / "pyvenv.cfg").write_text("relocatable = true\n", encoding="ascii")
        m = {
            "name": name,
            "venv": str(venv),
            "profile": "python",
            "python_resolved": "3.14.8",
            "robot_resolved": "",
            "environment_type": env_type,
            "project_path": project_path,
            "venv_owned_by_rfpy": True,
        }
        (env / "rfpy.json").write_text(json.dumps(m), encoding="utf-8")
        return env, venv

    def test_web_list_includes_project_pending(self):
        name = "project-visible"
        env, venv = self._make_fake_env(name, env_type="project")
        items = [x for x in self.rfpy.list_envs() if x["name"] == name]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["uv_mode"], "project-pending")

    def test_environment_type_shared_to_project_pending(self):
        name = "switch-shared-project"
        env, venv = self._make_fake_env(name, env_type="shared")
        out = self.rfpy.set_environment_type(name, "project")
        self.assertEqual(out["environment_type"], "project")
        self.assertEqual(out["project_path"], "")
        self.assertEqual(out["uv_mode"], "project-pending")
        self.assertEqual(Path(out["venv"]), venv)

    def test_web_has_type_switch_and_integrated_folder_browser(self):
        html = self.rfpy.WEB_HTML
        self.assertIn("/api/environment-type", html)
        self.assertIn("changeEnvType", html)
        self.assertIn("folderModal", html)
        self.assertIn("openFolderBrowser", html)
        self.assertIn("cache='no-store'", html)


    def test_web_removes_backend_native_pickers(self):
        root = Path(__file__).resolve().parents[1]
        app = (root / "rfpy.py").read_text(encoding="utf-8")
        self.assertNotIn("FolderBrowserDialog", app)
        self.assertNotIn("OpenFileDialog", app)
        self.assertNotIn("SetForegroundWindow", app)
        self.assertNotIn("/api/pick-folder", app)
        self.assertNotIn("/api/pick-file", app)

    def test_web_has_filesystem_browser(self):
        html = self.rfpy.WEB_HTML
        app = (Path(__file__).resolve().parents[1] / "rfpy.py").read_text(encoding="utf-8")
        self.assertIn("/api/fs/roots", app)
        self.assertIn("/api/fs/list", app)
        self.assertIn("/api/fs/mkdir", app)
        self.assertIn("folderModal", html)
        self.assertIn("openFolderBrowser", html)
        self.assertIn("fsChooseCurrent", html)

    def test_ca_uses_browser_file_input(self):
        html = self.rfpy.WEB_HTML
        app = (Path(__file__).resolve().parents[1] / "rfpy.py").read_text(encoding="utf-8")
        self.assertIn('type="file"', html)
        self.assertIn('accept=".pem,.crt,.cer"', html)
        self.assertIn("/api/upload-ca", app)
        self.assertIn("save_uploaded_ca", app)

    def test_public_version_is_1_0_0(self):
        self.assertEqual(self.rfpy.APP_VERSION, '1.0.0')

    def test_ai_profiles_are_built_in_without_local_model_profile(self):
        cfg = self.rfpy.load_config()
        self.assertIn('IA / LLM', cfg['installation_profiles'])
        self.assertIn('IA / LLM + Ollama', cfg['installation_profiles'])
        self.assertIn('rf-mcp', cfg['installation_profiles']['IA / LLM'])
        self.assertIn('pyyaml', cfg['installation_profiles']['IA / LLM'])
        self.assertIn('ollama', cfg['installation_profiles']['IA / LLM + Ollama'])
        self.assertNotIn('IA / LLM + Ollama + modèle local', cfg['installation_profiles'])
        self.assertEqual(cfg['profile_actions']['IA / LLM + Ollama'], ['ollama-runtime'])

    def test_ollama_runtime_install_does_not_pull_a_model(self):
        root = Path(__file__).resolve().parents[1]
        app = (root / 'rfpy.py').read_text(encoding='utf-8')
        block = app[app.index('def ensure_ollama_runtime'):app.index('def run_profile_actions')]
        self.assertIn('OllamaSetup.exe', block)
        self.assertNotIn('ollama pull', block.lower())
        self.assertNotIn('/api/pull', block.lower())

    def test_cli_doctor_output_is_not_discarded_by_powershell_bridge(self):
        root = Path(__file__).resolve().parents[1]
        ps = (root / 'rfpy.ps1').read_text(encoding='utf-8')
        default = ps[ps.index('default {'):ps.index('    }\n} catch', ps.index('default {'))]
        self.assertIn('Call-RfpyCore $forward', default)
        self.assertNotIn('Out-Null', default)
        self.assertNotIn('[void](Call-RfpyCore $forward)', default)

    def test_installer_has_native_root_dialog_and_parameter_bypass(self):
        root = Path(__file__).resolve().parents[1]
        installer = (root / 'rfpy-installer.ps1').read_text(encoding='utf-8')
        self.assertIn('Select-RfpyInstallDirectory', installer)
        self.assertIn('FolderBrowserDialog', installer)
        self.assertIn("$form.TopMost = $true", installer)
        self.assertIn("if (-not $InstallDirExplicit)", installer)
        self.assertIn("-InstallDir", installer)

    def test_custom_install_root_is_forwarded_to_backend(self):
        root = Path(__file__).resolve().parents[1]
        ps = (root / 'rfpy.ps1').read_text(encoding='utf-8')
        cmd = (root / 'rfpy.cmd').read_text(encoding='utf-8')
        installer = (root / 'rfpy-installer.ps1').read_text(encoding='utf-8')
        self.assertIn('$env:RFPY_HOME = $RfpyRoot', ps)
        self.assertIn('set "RFPY_HOME=%RFPY_ROOT%"', cmd)
        self.assertIn('$env:RFPY_HOME = $InstallDir', installer)


    def test_profile_actions_apply_when_completing_an_existing_environment(self):
        root = Path(__file__).resolve().parents[1]
        app = (root / 'rfpy.py').read_text(encoding='utf-8')
        block = app[app.index('def install_selected_packages'):app.index('def run_smoke_test')]
        self.assertIn('run_profile_actions(selected_profile,cfg,log)', block)
        self.assertIn("profile:$('installationProfile').value", self.rfpy.WEB_HTML)

    def test_author_notice_and_license_metadata(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(self.rfpy.AUTHOR, 'Olivier RENAULT')
        self.assertEqual(self.rfpy.LICENSE_ID, 'Apache-2.0')
        notice = (root / 'NOTICE').read_text(encoding='utf-8')
        self.assertIn('Olivier RENAULT', notice)
        self.assertIn('Apache License', notice)

    def test_profile_import_from_requirements(self):
        out = self.rfpy.parse_profile_dependency_file(
            'requirements.txt',
            'requests>=2.32\nPyYAML==6.0.3\n# comment\n--index-url https://example.invalid/simple\n',
        )
        self.assertEqual(out['packages'], ['requests>=2.32', 'PyYAML==6.0.3'])
        self.assertTrue(any('index-url' in x for x in out['warnings']))

    def test_profile_import_from_pyproject(self):
        out = self.rfpy.parse_profile_dependency_file(
            'pyproject.toml',
            '[project]\nname="demo"\nversion="0.1"\ndependencies=["requests>=2", "pyyaml"]\n\n[project.optional-dependencies]\ndev=["pytest"]\n',
        )
        self.assertEqual(out['packages'], ['requests>=2', 'pyyaml'])
        self.assertTrue(any('optional-dependencies' in x for x in out['warnings']))

    def test_msvc_binary_fallback_is_targeted_and_configurable(self):
        cfg = self.rfpy.load_config()
        self.assertTrue(cfg['package_install']['binary_fallback_on_msvc_error'])
        root = Path(__file__).resolve().parents[1]
        app = (root / 'rfpy.py').read_text(encoding='utf-8')
        self.assertIn('MSVC_BUILD_ERROR_RE', app)
        self.assertIn('"--only-binary", failed_name, failed_req', app)
        self.assertNotIn('"--only-binary", ":all:"', app)

    def test_msvc_binary_fallback_retries_only_failed_package(self):
        original_run = self.rfpy.run_process
        original_uv = self.rfpy.uv_path
        calls = []
        try:
            self.rfpy.uv_path = lambda: 'uv'
            responses = [
                (1, ['error: Failed to build `pyyaml==6.0.3`', 'error: Microsoft Visual C++ 14.0 or greater is required.']),
                (0, ['installed wheel']),
                (0, ['done']),
            ]
            def fake_run(args, **kwargs):
                calls.append(list(args))
                return responses.pop(0)
            self.rfpy.run_process = fake_run
            self.rfpy.install_packages(Path('python.exe'), ['rf-mcp', 'pyyaml', 'python-dotenv'], self.rfpy.load_config(), lambda x: None, 'test')
            self.assertEqual(len(calls), 3)
            self.assertIn('--only-binary', calls[1])
            ix = calls[1].index('--only-binary')
            self.assertEqual(calls[1][ix + 1].lower(), 'pyyaml')
            self.assertIn('pyyaml==6.0.3', [x.lower() for x in calls[1]])
            self.assertNotIn(':all:', calls[1])
        finally:
            self.rfpy.run_process = original_run
            self.rfpy.uv_path = original_uv

    def test_profiles_install_stays_in_profiles_tab(self):
        html = self.rfpy.WEB_HTML
        start = html.index('async function installPackages()')
        block = html[start:start + 1000]
        self.assertIn("jobKind='packages'", block)
        self.assertIn("$('profileExecution').open=true", block)
        self.assertNotIn("[data-page=\"install\"]", block)

    def test_web_has_cancel_and_profile_import_controls(self):
        html = self.rfpy.WEB_HTML
        self.assertIn('/api/jobs/cancel', html)
        self.assertIn('/api/profile/import', html)
        self.assertIn('profileImportFile', html)
        self.assertIn('stopProfileJob', html)
        self.assertIn('stopInstallJob', html)

    def test_open_file_uses_detached_helper(self):
        root = Path(__file__).resolve().parents[1]
        app = (root / 'rfpy.py').read_text(encoding='utf-8')
        block = app[app.index('def open_local_path'):app.index('def probe_project')]
        self.assertIn('DETACHED_PROCESS', block)
        self.assertIn('subprocess.DEVNULL', block)
        self.assertIn('os.startfile(sys.argv[1])', block)

    def test_job_cancel_stops_running_process(self):
        job_id = self.rfpy.JOBS.create(
            'cancel-test',
            lambda log: self.rfpy.run_process(
                [sys.executable, '-c', 'import time; print("started", flush=True); time.sleep(30)'],
                on_line=log,
            ),
        )
        deadline = time.time() + 3
        while time.time() < deadline:
            state = self.rfpy.JOBS.get(job_id)
            if state and 'started' in state.get('logs', []):
                break
            time.sleep(0.02)
        self.rfpy.JOBS.cancel(job_id)
        deadline = time.time() + 3
        state = None
        while time.time() < deadline:
            state = self.rfpy.JOBS.get(job_id)
            if state and state['status'] == 'cancelled':
                break
            time.sleep(0.02)
        self.assertIsNotNone(state)
        self.assertEqual(state['status'], 'cancelled')

    def test_installer_embeds_notice_license_and_authors(self):
        root = Path(__file__).resolve().parents[1]
        installer = (root / 'rfpy-installer.ps1').read_text(encoding='utf-8')
        for token in ('$NoticeBase64', '$LicenseBase64', '$AuthorsBase64'):
            self.assertIn(token, installer)
        self.assertIn("Join-Path $InstallDir 'NOTICE'", installer)
        self.assertIn("Join-Path $InstallDir 'LICENSE'", installer)
        self.assertIn("Join-Path $InstallDir 'AUTHORS'", installer)


if __name__ == '__main__':
    unittest.main()
