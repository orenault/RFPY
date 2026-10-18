# RFPY
# Copyright © 2026 Olivier RENAULT
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import contextlib
import datetime as dt
import html as html_mod
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import threading
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

APP_VERSION = "1.0.0"
AUTHOR = "Olivier RENAULT"
LICENSE_ID = "Apache-2.0"
DEFAULT_HOME = Path(os.environ.get("RFPY_HOME", r"C:\RFPY" if os.name == "nt" else str(Path.home() / ".rfpy")))
HOME = DEFAULT_HOME
STACKS_DIR = HOME / "stacks"
CONFIG_DIR = HOME / "config"
CONFIG_FILE = CONFIG_DIR / "rfpy.json"
BIN_DIR = HOME / "bin"
TOOLS_DIR = HOME / "tools"
UV_EXE = TOOLS_DIR / "uv" / ("uv.exe" if os.name == "nt" else "uv")
RUNTIMES_DIR = HOME / "runtimes" / "python"
REPORTS_DIR = HOME / "reports"

DEFAULT_CONFIG: dict[str, Any] = {
    "schema": 1,
    "proxy": {
        "enabled": False,
        "url": "",
        "no_proxy": "localhost,127.0.0.1",
    },
    "artifact": {
        "enabled": False,
        "allow_public_pypi": True,
        "ca_bundle": "",
    },
    "package_install": {
        "binary_fallback_on_msvc_error": True,
    },
    "cancellation": {
        "cleanup_new_environment": True,
    },
    "repositories": [
        {
            "name": "PyPI",
            "type": "pypi",
            "simple_url": "https://pypi.org/simple",
            "browse_url": "",
            "enabled": True,
            "install_all": False,
            "strict": True,
            "priority": 1000,
        }
    ],
    "defaults": {
        "python": "",
        "robot": "",
        "profile": "playwright",
        "browser": "chromium",
        "environment_type": "project",
    },
    "web": {"host": "127.0.0.1", "port": 0, "open_browser": True},
    "ui": {"language": "fr"},
    "version_filters": {
        "python_recent_only": True,
        "robot_recent_only": True,
        "python_min": "3.10",
        "robot_min": "6.0",
    },
    "default_environment": "",
    "installation_profiles": {
        "Python - Utilitaires": ["pyyaml", "python-dotenv"],
        "RF Web - Playwright": ["robotframework-browser", "robotframework-browser-batteries"],
        "RF Web - Selenium": ["robotframework-seleniumlibrary", "selenium"],
        "RF API": ["robotframework-requests"],
        "RF Data": ["robotframework-datadriver", "robotframework-jsonlibrary", "robotframework-faker"],
        "RF Database": ["robotframework-databaselibrary"],
        "RF SSH": ["robotframework-sshlibrary"],
        "RF Quality / Parallel": ["robotframework-pabot", "robotframework-robocop"],
        "IA / LLM": ["rf-mcp", "pyyaml", "python-dotenv"],
        "IA / LLM + Ollama": ["rf-mcp", "pyyaml", "python-dotenv", "ollama"]
    },
    "profile_actions": {
        "IA / LLM + Ollama": ["ollama-runtime"]
    },
    # Ancien nom conservé pour migration des configurations 2.2.x.
    "package_sets": {
        "RF Web - Playwright": ["robotframework-browser", "robotframework-browser-batteries"],
        "RF Web - Selenium": ["robotframework-seleniumlibrary", "selenium"],
        "RF API": ["robotframework-requests"],
        "RF Data": ["robotframework-datadriver", "robotframework-jsonlibrary", "robotframework-faker"],
        "RF Database": ["robotframework-databaselibrary"],
        "RF SSH": ["robotframework-sshlibrary"],
        "RF Quality / Parallel": ["robotframework-pabot", "robotframework-robocop"]
    },
}

STANDARD_LIBRARY_MODULES = [
    ("asyncio", "Programmation asynchrone"),
    ("json", "JSON"),
    ("pathlib", "Chemins/fichiers"),
    ("sqlite3", "SQLite"),
    ("ssl", "TLS/SSL"),
    ("urllib", "HTTP/URL standard"),
    ("venv", "Environnements virtuels"),
    ("unittest", "Tests unitaires"),
    ("xml", "XML"),
]

THIRD_PARTY_CATALOG = [
    ("robotframework", "Robot Framework", "Core"),
    ("robotframework-pabot", "Pabot - parallel execution", "Core"),
    ("robotframework-robocop", "Robocop - quality/lint", "Core"),
    ("robotframework-browser", "Browser Library", "Web"),
    ("robotframework-browser-batteries", "BrowserBatteries", "Web"),
    ("robotframework-seleniumlibrary", "SeleniumLibrary", "Web"),
    ("selenium", "Selenium Python", "Web"),
    ("robotframework-seleniumtestability", "SeleniumTestability", "Web"),
    ("robotframework-requests", "RequestsLibrary", "API"),
    ("robotframework-soaplibrary", "SOAPLibrary", "API"),
    ("robotframework-datadriver", "DataDriver", "Data"),
    ("robotframework-jsonlibrary", "JSONLibrary", "Data"),
    ("robotframework-csvlibrary", "CSVLibrary", "Data"),
    ("robotframework-faker", "Faker Library", "Data"),
    ("robotframework-crypto", "Crypto Library", "Data"),
    ("robotframework-databaselibrary", "DatabaseLibrary", "Database"),
    ("robotframework-sshlibrary", "SSHLibrary", "System"),
    ("robotframework-excellib", "ExcelLibrary", "Documents"),
    ("robotframework-pdf2", "PDF Library", "Documents"),
    ("robotframework-appiumlibrary", "AppiumLibrary", "Mobile"),
    ("robotframework-sikulilibrary", "SikuliLibrary", "Desktop"),
    ("rpaframework", "RPA Framework", "RPA / Desktop"),
    ("RESTinstance", "RESTinstance", "API"),
    ("robotframework-archivelibrary", "ArchiveLibrary", "Files / Archive"),
    ("robotframework-imaplibrary2", "ImapLibrary2", "Messaging"),
    ("robotframework-ftplibrary", "FTPLibrary", "System"),
    ("robotframework-scplibrary", "SCPLibrary", "System"),
    ("requests", "requests", "Python support"),
    ("httpx", "httpx", "Python support"),
    ("numpy", "NumPy", "Python support"),
    ("pandas", "pandas", "Python support"),
    ("openpyxl", "openpyxl", "Python support"),
    ("xlrd", "xlrd", "Python support"),
    ("pyyaml", "PyYAML", "Python support"),
    ("jsonschema", "jsonschema", "Python support"),
    ("lxml", "lxml", "Python support"),
    ("beautifulsoup4", "BeautifulSoup", "Python support"),
    ("paramiko", "Paramiko", "Python support"),
    ("sqlalchemy", "SQLAlchemy", "Python support"),
    ("oracledb", "Oracle DB driver", "Python support"),
    ("psycopg", "PostgreSQL driver", "Python support"),
    ("pymysql", "MySQL driver", "Python support"),
    ("boto3", "AWS SDK", "Python support"),
    ("python-dotenv", "python-dotenv", "Python support"),
    ("rf-mcp", "RF-MCP / RobotMCP", "AI / LLM"),
    ("ollama", "Ollama Python client", "AI / LLM")
]

_metadata_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_metadata_lock = threading.Lock()


class RfpyError(RuntimeError):
    pass


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_dirs() -> None:
    for p in (HOME, STACKS_DIR, CONFIG_DIR, BIN_DIR, TOOLS_DIR, RUNTIMES_DIR, REPORTS_DIR):
        p.mkdir(parents=True, exist_ok=True)


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(base))
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> dict[str, Any]:
    ensure_dirs()
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
        cfg = deep_merge(DEFAULT_CONFIG, raw)
        # Migration 2.2.x : les anciens "package_sets" deviennent des profils
        # d installation. On conserve l ancien champ pour compatibilité.
        if raw.get("package_sets") and not raw.get("installation_profiles"):
            cfg["installation_profiles"] = dict(raw.get("package_sets") or {})
        cfg.setdefault("ui", {}).setdefault("language", "fr")
        cfg.setdefault("profile_actions", {})
        cfg.setdefault("version_filters", {})
        cfg["version_filters"].setdefault("python_recent_only", True)
        cfg["version_filters"].setdefault("robot_recent_only", True)
        cfg["version_filters"].setdefault("python_min", "3.10")
        cfg["version_filters"].setdefault("robot_min", "6.0")
        # Anciennes configurations 1.0.0 pouvaient avoir le sélecteur de dépôts
        # privés activé par défaut alors qu'aucun dépôt privé n'était renseigné.
        # Dans ce cas uniquement, revenir à l'état sûr/inactif.
        private_repos = [
            r for r in (cfg.get("repositories") or [])
            if str(r.get("type", "")).lower() != "pypi"
            and r.get("enabled", True)
            and str(r.get("simple_url", "")).strip()
        ]
        if cfg.get("artifact", {}).get("enabled") and not private_repos:
            cfg.setdefault("artifact", {})["enabled"] = False
        return cfg
    except Exception as exc:
        raise RfpyError(f"Configuration illisible: {CONFIG_FILE}: {exc}") from exc


def save_config(cfg: dict[str, Any]) -> None:
    ensure_dirs()
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


SUPPORTED_LANGUAGES = ("fr", "en", "de", "es", "zh")
LANGUAGE_NAMES = {
    "fr": "Français",
    "en": "English",
    "de": "Deutsch",
    "es": "Español",
    "zh": "中文",
}

CLI_I18N: dict[str, dict[str, str]] = {
    "fr": {
        "title": "RFPY - gestionnaire d'environnements Python + Robot Framework",
        "usage": "UTILISATION",
        "commands": "COMMANDES",
        "menu": "Menu interactif de gestion",
        "examples": "EXEMPLES",
        "language": "Langue",
        "project_type": "Projet : environnement dédié à un projet, avec .venv dans le projet.",
        "shared_type": "Partagé : environnement réutilisable sous RFPY/stacks.",
        "list": "Lister les environnements",
        "activate": "Activer un environnement dans le shell courant",
        "deactivate": "Désactiver l'environnement courant",
        "status": "Afficher l'environnement courant",
        "doctor": "Diagnostiquer l'installation RFPY",
        "web": "Ouvrir la console Web locale",
        "install": "Créer un nouvel environnement",
        "rename": "Renommer un environnement",
        "delete": "Supprimer un environnement",
        "default": "Définir l'environnement par défaut",
        "packages": "Lister les packages d'un environnement",
        "add_packages": "Ajouter des packages à un environnement",
        "export": "Générer requirements.txt, pyproject.toml ou SBOM",
        "test": "Lancer un smoke test",
        "duplicate": "Dupliquer un environnement",
        "project": "Créer ou adopter un environnement Projet",
        "config": "Afficher la configuration",
        "lang": "Afficher ou modifier la langue CLI/Web",
        "types": "Expliquer les types Projet et Partagé",
        "install_options": "OPTIONS D'INSTALLATION",
        "install_examples": "EXEMPLES D'INSTALLATION",
        "name": "Nom de l'environnement",
        "python": "Version Python (ex. 3.14 ou 3.14.8)",
        "robot": "Version Robot Framework (ex. latest, 7.4.2 ou none)",
        "profile": "Socle : python, robot, playwright ou selenium",
        "type": "Type : project ou shared",
        "project_path": "Dossier projet pour un environnement project",
        "existing": "Gestion d'un .venv existant : use, recreate ou fail",
        "install_profile": "Profil de bibliothèques à appliquer après le socle",
        "lang_prompt": "Choisissez la langue",
        "lang_saved": "Langue enregistrée",
        "cancel": "Annulé",
    },
    "en": {
        "title": "RFPY - Python + Robot Framework environment manager",
        "usage": "USAGE", "commands": "COMMANDS",
        "menu": "Interactive management menu", "examples": "EXAMPLES", "language": "Language",
        "project_type": "Project: dedicated environment with .venv inside the project.",
        "shared_type": "Shared: reusable environment under RFPY/stacks.",
        "list": "List environments", "activate": "Activate an environment in the current shell",
        "deactivate": "Deactivate the current environment", "status": "Show the current environment",
        "doctor": "Diagnose the RFPY installation", "web": "Open the local Web console",
        "install": "Create a new environment", "rename": "Rename an environment", "delete": "Delete an environment",
        "default": "Set the default environment", "packages": "List packages in an environment",
        "add_packages": "Add packages to an environment", "export": "Generate requirements.txt, pyproject.toml or SBOM",
        "test": "Run a smoke test", "duplicate": "Duplicate an environment", "project": "Create or adopt a Project environment",
        "config": "Show configuration", "lang": "Show or change CLI/Web language", "types": "Explain Project and Shared types",
        "install_options": "INSTALL OPTIONS", "install_examples": "INSTALL EXAMPLES", "name": "Environment name",
        "python": "Python version (e.g. 3.14 or 3.14.8)", "robot": "Robot Framework version (e.g. latest, 7.4.2 or none)",
        "profile": "Base stack: python, robot, playwright or selenium", "type": "Type: project or shared",
        "project_path": "Project folder for a project environment", "existing": "Existing .venv policy: use, recreate or fail",
        "install_profile": "Library profile applied after the base stack", "lang_prompt": "Choose the language",
        "lang_saved": "Language saved", "cancel": "Cancelled",
    },
    "de": {
        "title": "RFPY - Manager für Python- und Robot-Framework-Umgebungen",
        "usage": "VERWENDUNG", "commands": "BEFEHLE",
        "menu": "Interaktives Verwaltungsmenü", "examples": "BEISPIELE", "language": "Sprache",
        "project_type": "Projekt: dedizierte Umgebung mit .venv im Projekt.", "shared_type": "Geteilt: wiederverwendbare Umgebung unter RFPY/stacks.",
        "list": "Umgebungen auflisten", "activate": "Umgebung in der aktuellen Shell aktivieren", "deactivate": "Aktuelle Umgebung deaktivieren",
        "status": "Aktuelle Umgebung anzeigen", "doctor": "RFPY-Installation diagnostizieren", "web": "Lokale Web-Konsole öffnen",
        "install": "Neue Umgebung erstellen", "rename": "Umgebung umbenennen", "delete": "Umgebung löschen", "default": "Standardumgebung festlegen",
        "packages": "Pakete einer Umgebung auflisten", "add_packages": "Pakete zu einer Umgebung hinzufügen", "export": "requirements.txt, pyproject.toml oder SBOM erzeugen",
        "test": "Smoke-Test ausführen", "duplicate": "Umgebung duplizieren", "project": "Projektumgebung erstellen oder übernehmen",
        "config": "Konfiguration anzeigen", "lang": "CLI/Web-Sprache anzeigen oder ändern", "types": "Projekt- und Geteilt-Typen erklären",
        "install_options": "INSTALLATIONSOPTIONEN", "install_examples": "INSTALLATIONSBEISPIELE", "name": "Name der Umgebung",
        "python": "Python-Version (z. B. 3.14 oder 3.14.8)", "robot": "Robot-Framework-Version (z. B. latest, 7.4.2 oder none)",
        "profile": "Basis: python, robot, playwright oder selenium", "type": "Typ: project oder shared", "project_path": "Projektordner für eine project-Umgebung",
        "existing": "Vorhandenes .venv: use, recreate oder fail", "install_profile": "Bibliotheksprofil nach der Basisinstallation",
        "lang_prompt": "Sprache auswählen", "lang_saved": "Sprache gespeichert", "cancel": "Abgebrochen",
    },
    "es": {
        "title": "RFPY - gestor de entornos Python + Robot Framework",
        "usage": "USO", "commands": "COMANDOS",
        "menu": "Menú interactivo de gestión", "examples": "EJEMPLOS", "language": "Idioma",
        "project_type": "Proyecto: entorno dedicado con .venv dentro del proyecto.", "shared_type": "Compartido: entorno reutilizable en RFPY/stacks.",
        "list": "Listar entornos", "activate": "Activar un entorno en la shell actual", "deactivate": "Desactivar el entorno actual",
        "status": "Mostrar el entorno actual", "doctor": "Diagnosticar la instalación RFPY", "web": "Abrir la consola Web local",
        "install": "Crear un nuevo entorno", "rename": "Renombrar un entorno", "delete": "Eliminar un entorno", "default": "Definir el entorno predeterminado",
        "packages": "Listar paquetes de un entorno", "add_packages": "Añadir paquetes a un entorno", "export": "Generar requirements.txt, pyproject.toml o SBOM",
        "test": "Ejecutar un smoke test", "duplicate": "Duplicar un entorno", "project": "Crear o adoptar un entorno Proyecto",
        "config": "Mostrar la configuración", "lang": "Mostrar o cambiar el idioma CLI/Web", "types": "Explicar los tipos Proyecto y Compartido",
        "install_options": "OPCIONES DE INSTALACIÓN", "install_examples": "EJEMPLOS DE INSTALACIÓN", "name": "Nombre del entorno",
        "python": "Versión Python (p. ej. 3.14 o 3.14.8)", "robot": "Versión Robot Framework (p. ej. latest, 7.4.2 o none)",
        "profile": "Base: python, robot, playwright o selenium", "type": "Tipo: project o shared", "project_path": "Carpeta de proyecto para un entorno project",
        "existing": ".venv existente: use, recreate o fail", "install_profile": "Perfil de bibliotecas aplicado después de la base",
        "lang_prompt": "Seleccione el idioma", "lang_saved": "Idioma guardado", "cancel": "Cancelado",
    },
    "zh": {
        "title": "RFPY - Python + Robot Framework 环境管理器",
        "usage": "用法", "commands": "命令",
        "menu": "交互式管理菜单", "examples": "示例", "language": "语言",
        "project_type": "项目：专用于一个项目，.venv 位于项目目录中。", "shared_type": "共享：位于 RFPY/stacks 下的可复用环境。",
        "list": "列出环境", "activate": "在当前 shell 中激活环境", "deactivate": "停用当前环境", "status": "显示当前环境",
        "doctor": "诊断 RFPY 安装", "web": "打开本地 Web 控制台", "install": "创建新环境", "rename": "重命名环境", "delete": "删除环境",
        "default": "设置默认环境", "packages": "列出环境中的包", "add_packages": "向环境添加包", "export": "生成 requirements.txt、pyproject.toml 或 SBOM",
        "test": "运行冒烟测试", "duplicate": "复制环境", "project": "创建或接管项目环境", "config": "显示配置",
        "lang": "显示或更改 CLI/Web 语言", "types": "说明项目和共享类型", "install_options": "安装选项", "install_examples": "安装示例",
        "name": "环境名称", "python": "Python 版本（如 3.14 或 3.14.8）", "robot": "Robot Framework 版本（如 latest、7.4.2 或 none）",
        "profile": "基础环境：python、robot、playwright 或 selenium", "type": "类型：project 或 shared", "project_path": "project 环境的项目目录",
        "existing": "已有 .venv 的处理方式：use、recreate 或 fail", "install_profile": "基础安装后应用的库配置",
        "lang_prompt": "请选择语言", "lang_saved": "语言已保存", "cancel": "已取消",
    },
}


CLI_RUNTIME_I18N: dict[str, dict[str, str]] = {
    "fr": {
        "no_envs": "Aucun environnement RFPY.", "no_active": "Aucun environnement RFPY actif.",
        "name": "Nom", "type": "Type", "profile": "Profil", "robot": "Robot Framework", "project": "Projet",
        "project_kind": "Projet", "shared_kind": "Partagé", "default_set": "Environnement par défaut : {name}",
        "wrapper_required": "Cette commande doit être lancée via `rfpy` afin de modifier le shell courant.",
        "menu_wrapper": "Le menu interactif est fourni par le wrapper `rfpy -m` afin de pouvoir modifier le shell courant.",
        "types": "Projet (recommandé pour le développement)\n  Un seul projet, venv=<projet>/.venv, UV_PROJECT configuré.\n  Commandes uv projet normales : add/remove/sync/run/build.\n\nPartagé\n  Venv réutilisable sous RFPY/stacks.\n  Utiliser uv pip install/list/freeze ; uv run est forcé en --no-project.\n  Les commandes uv de projet sont protégées pour éviter les erreurs.",
        "first_run": "Aucun environnement n'existe encore. Ouverture de la console Web...",
        "direct_backend": "Le backend Python RFPY a été appelé directement sans argument."
    },
    "en": {
        "no_envs": "No RFPY environment.", "no_active": "No active RFPY environment.",
        "name": "Name", "type": "Type", "profile": "Profile", "robot": "Robot Framework", "project": "Project",
        "project_kind": "Project", "shared_kind": "Shared", "default_set": "Default environment: {name}",
        "wrapper_required": "This command must be run through `rfpy` so the current shell can be modified.",
        "menu_wrapper": "The interactive menu is provided by the `rfpy -m` wrapper so it can modify the current shell.",
        "types": "Project (recommended for development)\n  One project, venv=<project>/.venv, UV_PROJECT configured.\n  Normal uv project commands: add/remove/sync/run/build.\n\nShared\n  Reusable venv under RFPY/stacks.\n  Use uv pip install/list/freeze; uv run is forced with --no-project.\n  uv project commands are protected to prevent mistakes.",
        "first_run": "No environment exists yet. Opening the Web console...",
        "direct_backend": "The RFPY Python backend was called directly without arguments."
    },
    "de": {
        "no_envs": "Keine RFPY-Umgebung.", "no_active": "Keine aktive RFPY-Umgebung.",
        "name": "Name", "type": "Typ", "profile": "Profil", "robot": "Robot Framework", "project": "Projekt",
        "project_kind": "Projekt", "shared_kind": "Geteilt", "default_set": "Standardumgebung: {name}",
        "wrapper_required": "Dieser Befehl muss über `rfpy` gestartet werden, damit die aktuelle Shell geändert werden kann.",
        "menu_wrapper": "Das interaktive Menü wird vom Wrapper `rfpy -m` bereitgestellt, damit die aktuelle Shell geändert werden kann.",
        "types": "Projekt (für Entwicklung empfohlen)\n  Ein Projekt, venv=<Projekt>/.venv, UV_PROJECT konfiguriert.\n  Normale uv-Projektbefehle: add/remove/sync/run/build.\n\nGeteilt\n  Wiederverwendbares venv unter RFPY/stacks.\n  uv pip install/list/freeze verwenden; uv run wird mit --no-project ausgeführt.\n  uv-Projektbefehle sind zum Schutz vor Fehlern gesperrt.",
        "first_run": "Noch keine Umgebung vorhanden. Web-Konsole wird geöffnet...",
        "direct_backend": "Das RFPY-Python-Backend wurde direkt ohne Argumente aufgerufen."
    },
    "es": {
        "no_envs": "No hay entornos RFPY.", "no_active": "No hay un entorno RFPY activo.",
        "name": "Nombre", "type": "Tipo", "profile": "Perfil", "robot": "Robot Framework", "project": "Proyecto",
        "project_kind": "Proyecto", "shared_kind": "Compartido", "default_set": "Entorno predeterminado: {name}",
        "wrapper_required": "Este comando debe ejecutarse mediante `rfpy` para poder modificar la shell actual.",
        "menu_wrapper": "El menú interactivo lo proporciona el wrapper `rfpy -m` para poder modificar la shell actual.",
        "types": "Proyecto (recomendado para desarrollo)\n  Un proyecto, venv=<proyecto>/.venv, UV_PROJECT configurado.\n  Comandos uv normales: add/remove/sync/run/build.\n\nCompartido\n  Venv reutilizable en RFPY/stacks.\n  Use uv pip install/list/freeze; uv run se fuerza con --no-project.\n  Los comandos de proyecto de uv están protegidos para evitar errores.",
        "first_run": "Todavía no existe ningún entorno. Abriendo la consola Web...",
        "direct_backend": "El backend Python de RFPY se ha llamado directamente sin argumentos."
    },
    "zh": {
        "no_envs": "没有 RFPY 环境。", "no_active": "没有活动的 RFPY 环境。",
        "name": "名称", "type": "类型", "profile": "配置", "robot": "Robot Framework", "project": "项目",
        "project_kind": "项目", "shared_kind": "共享", "default_set": "默认环境：{name}",
        "wrapper_required": "必须通过 `rfpy` 运行此命令，才能修改当前 shell。",
        "menu_wrapper": "交互菜单由 `rfpy -m` 包装器提供，以便修改当前 shell。",
        "types": "项目（推荐用于开发）\n  单一项目，venv=<项目>/.venv，并配置 UV_PROJECT。\n  正常使用 uv 项目命令：add/remove/sync/run/build。\n\n共享\n  RFPY/stacks 下的可复用 venv。\n  使用 uv pip install/list/freeze；uv run 强制使用 --no-project。\n  uv 项目命令受到保护以防误操作。",
        "first_run": "尚无环境。正在打开 Web 控制台...",
        "direct_backend": "RFPY Python 后端被直接调用且未提供参数。"
    },
}


def cli_runtime_text(key: str, **values: Any) -> str:
    lang = current_language()
    bucket = CLI_RUNTIME_I18N.get(lang, CLI_RUNTIME_I18N["en"])
    template = bucket.get(key, CLI_RUNTIME_I18N["en"].get(key, key))
    return template.format(**values)


def current_language() -> str:
    try:
        lang = str(load_config().get("ui", {}).get("language", "fr") or "fr").lower()
    except Exception:
        lang = os.environ.get("RFPY_LANG", "fr").lower()
    return lang if lang in SUPPORTED_LANGUAGES else "fr"


def set_language(lang: str) -> str:
    lang = str(lang or "").lower()
    if lang not in SUPPORTED_LANGUAGES:
        raise RfpyError("Invalid language. Use: " + ", ".join(SUPPORTED_LANGUAGES))
    cfg = load_config()
    cfg.setdefault("ui", {})["language"] = lang
    save_config(cfg)
    return lang


def interactive_language() -> str:
    current = current_language()
    t = CLI_I18N[current]
    print(f"{t['lang_prompt']}:")
    for idx, code in enumerate(SUPPORTED_LANGUAGES, 1):
        mark = "*" if code == current else " "
        print(f"  {idx}. {LANGUAGE_NAMES[code]} ({code}) {mark}")
    try:
        raw = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print(t["cancel"])
        return current
    if not raw:
        return current
    if raw.isdigit() and 1 <= int(raw) <= len(SUPPORTED_LANGUAGES):
        lang = SUPPORTED_LANGUAGES[int(raw) - 1]
    else:
        lang = raw.lower()
    lang = set_language(lang)
    print(f"[RFPY] {CLI_I18N[lang]['lang_saved']}: {LANGUAGE_NAMES[lang]} ({lang})")
    return lang


def print_cli_help(target: list[str] | None = None) -> None:
    target = [str(x).lower() for x in (target or []) if str(x).strip()]
    lang = current_language()
    t = CLI_I18N[lang]
    aliases = {"on": "activate", "off": "deactivate", "lang": "language"}
    if target:
        target[0] = aliases.get(target[0], target[0])
    command = " ".join(target[:2]) if target[:2] == ["project", "add"] else (target[0] if target else "")

    if command == "install":
        print(t["title"])
        print()
        print(f"{t['usage']}: rfpy install NAME [options]")
        print()
        print(t["install_options"])
        rows = [
            ("NAME", t["name"]), ("--python VERSION", t["python"]), ("--robot VERSION", t["robot"]),
            ("--profile PROFILE", t["profile"]), ("--type project|shared", t["type"]),
            ("--project PATH", t["project_path"]), ("--existing use|recreate|fail", t["existing"]),
            ("--install-profile NAME", t["install_profile"]),
        ]
        for opt, desc in rows:
            print(f"  {opt:<34} {desc}")
        print()
        print(t["install_examples"])
        print("  rfpy install RF-TOOLS --type shared --python 3.14 --robot latest --profile robot")
        print("  rfpy install WEB-PW --type shared --python 3.14 --robot latest --profile playwright")
        print(r"  rfpy install MYAPP --type project --project C:\dev\myapp --python 3.14 --profile playwright")
        print('  rfpy install AI --type shared --python 3.14 --profile python --install-profile "IA / LLM + Ollama"')
        return

    if command == "project add":
        print(t["title"]); print(); print(f"{t['usage']}: rfpy project add PATH [--name NAME] [--python VERSION] [--robot VERSION] [--profile PROFILE] [--existing POLICY]")
        print(); print(t["examples"]); print(r"  rfpy project add C:\dev\demo --python 3.14"); print(r"  rfpy project add C:\dev\demo --name DEMO --python 3.14 --profile playwright")
        return

    if command == "language":
        print(t["title"]); print(); print(f"{t['usage']}: rfpy language [fr|en|de|es|zh]"); print("  rfpy language"); print("  rfpy language en")
        return

    descriptions = [
        ("rfpy", t["activate"]), ("rfpy -m", t["menu"]), ("rfpy list", t["list"]),
        ("rfpy activate ENV", t["activate"]), ("rfpy deactivate", t["deactivate"]), ("rfpy status", t["status"]),
        ("rfpy doctor", t["doctor"]), ("rfpy web", t["web"]), ("rfpyw", t["web"]),
        ("rfpy install ...", t["install"]), ("rfpy project add ...", t["project"]), ("rfpy rename OLD NEW", t["rename"]),
        ("rfpy delete ENV", t["delete"]), ("rfpy default ENV", t["default"]), ("rfpy packages ENV", t["packages"]),
        ("rfpy add-packages ENV PKG...", t["add_packages"]), ("rfpy export ENV KIND", t["export"]),
        ("rfpy test ENV", t["test"]), ("rfpy duplicate ENV NEW", t["duplicate"]),
        ("rfpy language [LANG]", t["lang"]), ("rfpy config [show|path]", t["config"]), ("rfpy types", t["types"]),
    ]
    print(t["title"])
    print(f"{t['language']}: {LANGUAGE_NAMES[lang]} ({lang})")
    print()
    print(t["usage"])
    print("  rfpy [command] [options]")
    print("  rfpy -h | --help | -help | /?")
    print("  rfpy COMMAND -h")
    print()
    print(t["commands"])
    for syntax, desc in descriptions:
        print(f"  {syntax:<38} {desc}")
    print()
    print(t["project_type"])
    print(t["shared_type"])
    print()
    print(t["examples"])
    print("  rfpy")
    print("  rfpy -m")
    print("  rfpy install -h")
    print(r"  rfpy project add C:\dev\demo --python 3.14")
    print("  rfpy language en")
    print("  rfpy web")


def subprocess_env(cfg: dict[str, Any] | None = None) -> dict[str, str]:
    cfg = cfg or load_config()
    env = os.environ.copy()
    proxy = cfg.get("proxy", {})
    if proxy.get("enabled") and proxy.get("url"):
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            env[key] = str(proxy["url"])
        no_proxy = str(proxy.get("no_proxy", ""))
        if no_proxy:
            env["NO_PROXY"] = no_proxy
            env["no_proxy"] = no_proxy
    else:
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            env.pop(key, None)
    ca = str(cfg.get("artifact", {}).get("ca_bundle", "") or "").strip()
    if ca:
        env["SSL_CERT_FILE"] = ca
        env["REQUESTS_CA_BUNDLE"] = ca
        env["NODE_EXTRA_CA_CERTS"] = ca
    return env


def url_opener(cfg: dict[str, Any] | None = None) -> urllib.request.OpenerDirector:
    cfg = cfg or load_config()
    handlers: list[Any] = []
    proxy = cfg.get("proxy", {})
    if proxy.get("enabled") and proxy.get("url"):
        handlers.append(urllib.request.ProxyHandler({"http": proxy["url"], "https": proxy["url"]}))
    else:
        handlers.append(urllib.request.ProxyHandler({}))
    ca = str(cfg.get("artifact", {}).get("ca_bundle", "") or "").strip()
    if ca:
        handlers.append(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca)))
    return urllib.request.build_opener(*handlers)


def http_get_text(url: str, timeout: float = 10.0, cfg: dict[str, Any] | None = None) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": f"RFPY/{APP_VERSION}"})
    with url_opener(cfg).open(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def http_get_json(url: str, timeout: float = 10.0, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    return json.loads(http_get_text(url, timeout=timeout, cfg=cfg))


def download_file(url: str, destination: Path, cfg: dict[str, Any] | None = None, log: Callable[[str], None] = print) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": f"RFPY/{APP_VERSION}"})
    log(f"[...] Téléchargement: {url}")
    try:
        with url_opener(cfg).open(req, timeout=120) as src, destination.open("wb") as dst:
            total = int(src.headers.get("Content-Length") or 0)
            done = 0
            next_pct = 10
            while True:
                if _job_is_cancelled():
                    raise JobCancelled("Téléchargement annulé par l'utilisateur.")
                block = src.read(1024 * 1024)
                if not block:
                    break
                dst.write(block)
                done += len(block)
                if total:
                    pct = int(done * 100 / total)
                    if pct >= next_pct:
                        log(f"[...] Téléchargement: {min(pct, 100)}%")
                        next_pct = min(100, ((pct // 10) + 1) * 10)
    except JobCancelled:
        with contextlib.suppress(Exception):
            destination.unlink(missing_ok=True)
        raise
    return destination


def find_ollama_executable() -> Path | None:
    found = shutil.which("ollama")
    if found:
        return Path(found)
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        candidates = [
            local / "Programs" / "Ollama" / "ollama.exe",
            local / "Ollama" / "ollama.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
    return None


def ensure_ollama_runtime(cfg: dict[str, Any], log: Callable[[str], None] = print) -> Path:
    """Install the Ollama Windows runtime only. No model is downloaded here."""
    current = find_ollama_executable()
    if current:
        log(f"[OK] Runtime Ollama déjà disponible: {current}")
        return current
    if os.name != "nt":
        raise RfpyError("L'installation automatique du runtime Ollama est actuellement disponible sous Windows uniquement.")

    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        raise RfpyError("Windows PowerShell est requis pour vérifier la signature de l'installateur Ollama.")

    setup = HOME / "tmp" / "ollama" / "OllamaSetup.exe"
    download_file("https://ollama.com/download/OllamaSetup.exe", setup, cfg=cfg, log=log)

    escaped = str(setup).replace("'", "''")
    verify = (
        f"$s=Get-AuthenticodeSignature -LiteralPath '{escaped}'; "
        "Write-Output $s.Status; if($s.Status -ne 'Valid'){exit 2}"
    )
    rc, lines = run_process([powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", verify], capture=True, check=False, cfg=cfg)
    if rc != 0:
        raise RfpyError("Signature Authenticode Ollama invalide ou non vérifiable: " + " ".join(lines[-3:]))
    log("[OK] Signature Authenticode Ollama valide")

    log("[...] Installation silencieuse du runtime Ollama (aucun modèle n'est téléchargé)")
    run_process([str(setup), "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES"], cfg=cfg, on_line=log)
    runtime = find_ollama_executable()
    if not runtime:
        expected = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        if expected.exists():
            runtime = expected
    if not runtime:
        raise RfpyError("Ollama a été installé mais son exécutable n'a pas été retrouvé. Ouvrez une nouvelle session Windows puis lancez `rfpy doctor`.")
    log(f"[OK] Runtime Ollama installé: {runtime}")
    return runtime


def run_profile_actions(profile_name: str, cfg: dict[str, Any], log: Callable[[str], None] = print) -> None:
    for action in (cfg.get("profile_actions", {}) or {}).get(profile_name, []) or []:
        if action == "ollama-runtime":
            ensure_ollama_runtime(cfg, log)
        else:
            log(f"[WARN] Action de profil inconnue ignorée: {action}")


class JobCancelled(RfpyError):
    """Raised when a Web/CLI background job is explicitly cancelled."""


_job_context = threading.local()


def _current_job_id() -> str:
    return str(getattr(_job_context, "job_id", "") or "")


def _job_is_cancelled() -> bool:
    job_id = _current_job_id()
    jobs = globals().get("JOBS")
    return bool(job_id and jobs is not None and jobs.is_cancelled(job_id))


def run_process(
    args: list[str],
    *,
    check: bool = True,
    capture: bool = False,
    cwd: Path | None = None,
    cfg: dict[str, Any] | None = None,
    on_line: Callable[[str], None] | None = None,
) -> tuple[int, list[str]]:
    if _job_is_cancelled():
        raise JobCancelled("Opération annulée par l'utilisateur.")
    env = subprocess_env(cfg)
    proc = subprocess.Popen(
        args,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    job_id = _current_job_id()
    jobs = globals().get("JOBS")
    if job_id and jobs is not None:
        jobs.register_process(job_id, proc)
    lines: list[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\r\n")
            lines.append(line)
            if not capture:
                if on_line:
                    on_line(line)
                else:
                    print(line, flush=True)
        rc = proc.wait()
    finally:
        with contextlib.suppress(Exception):
            if proc.stdout is not None:
                proc.stdout.close()
        if job_id and jobs is not None:
            jobs.clear_process(job_id, proc)
    if _job_is_cancelled():
        raise JobCancelled("Opération annulée par l'utilisateur.")
    if check and rc:
        detail = "\n".join(lines[-20:]) if capture else ""
        suffix = f"\n{detail}" if detail else ""
        raise RfpyError(f"Commande en échec ({rc}): {' '.join(args)}{suffix}")
    return rc, lines


def uv_path() -> str:
    if UV_EXE.exists():
        return str(UV_EXE)
    found = shutil.which("uv")
    if found:
        return found
    raise RfpyError("uv introuvable. Réinstallez RFPY ou lancez `rfpy doctor`.")


def stable_versions_from_uv(request: str | None = None) -> list[str]:
    cmd = [uv_path(), "python", "list"]
    if request:
        cmd.append(request)
    cmd.append("--all-versions")
    rc, lines = run_process(cmd, capture=True, check=False)
    if rc:
        return []
    versions: set[str] = set()
    pattern = re.compile(r"cpython-(\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?)", re.I)
    for line in lines:
        for m in pattern.finditer(line):
            versions.add(m.group(1))
    def sort_key(v: str) -> Version:
        try:
            return Version(v)
        except InvalidVersion:
            return Version("0")
    return sorted(versions, key=sort_key, reverse=True)


def resolve_python(requested: str) -> str:
    requested = requested.strip()
    if re.fullmatch(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?", requested, re.I):
        return requested
    versions = stable_versions_from_uv(None if requested == "latest" else requested)
    stable = [v for v in versions if not Version(v).is_prerelease]
    if requested != "latest":
        stable = [v for v in stable if v.startswith(requested + ".")]
    if not stable:
        raise RfpyError(f"Aucune version Python stable disponible pour {requested}.")
    return stable[0]


def find_managed_python(version: str) -> Path | None:
    candidates: list[Path] = []
    if not RUNTIMES_DIR.exists():
        return None
    for d in RUNTIMES_DIR.iterdir():
        if not d.is_dir() or not d.name.lower().startswith(f"cpython-{version.lower()}"):
            continue
        exe = d / ("python.exe" if os.name == "nt" else "bin/python")
        if exe.exists():
            candidates.append(exe)
    return sorted(candidates)[0] if candidates else None


def ensure_python(version_request: str, log: Callable[[str], None] = print) -> tuple[str, Path]:
    resolved = resolve_python(version_request)
    existing = find_managed_python(resolved)
    if existing:
        log(f"[OK] Python {resolved} déjà présent: {existing}")
        return resolved, existing
    log(f"[...] Installation de Python {resolved}")
    run_process([uv_path(), "python", "install", resolved, "--install-dir", str(RUNTIMES_DIR), "--no-bin"], on_line=log)
    exe = find_managed_python(resolved)
    if not exe:
        raise RfpyError(f"Python {resolved} installé mais exécutable introuvable sous {RUNTIMES_DIR}")
    return resolved, exe


def normalize_name(name: str) -> str:
    name = name.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name):
        raise RfpyError("Nom d'environnement invalide. Utiliser uniquement lettres, chiffres, '.', '_' et '-'.")
    return name


def stack_dir(name: str) -> Path:
    return STACKS_DIR / normalize_name(name)


def manifest_path(name: str) -> Path:
    return stack_dir(name) / "rfpy.json"


def read_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def list_envs(include_incomplete: bool = False) -> list[dict[str, Any]]:
    ensure_dirs()
    result: list[dict[str, Any]] = []
    cfg = load_config()
    default_env = str(cfg.get("default_environment", "") or "")
    for d in sorted(STACKS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not d.is_dir():
            continue
        mp = d / "rfpy.json"
        if not mp.exists():
            if include_incomplete:
                result.append({"name": d.name, "path": str(d), "complete": False, "reason": "manifest absent"})
            continue
        try:
            m = read_manifest(mp)
            venv = Path(m.get("venv", d / ".venv"))
            py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            complete = py.exists()
            env_type = str(m.get("environment_type") or "shared").lower()
            if env_type not in {"project", "shared"}:
                env_type = "shared"
            item = {
                "name": m.get("name", d.name),
                "path": str(d),
                "venv": str(venv),
                "python": m.get("python_resolved", "?"),
                "robot": m.get("robot_resolved", "-"),
                "profile": m.get("profile", "python"),
                "environment_type": env_type,
                "project_path": str(m.get("project_path") or ""),
                "uv_mode": ("project" if str(m.get("project_path") or "").strip() else "project-pending") if env_type == "project" else "active-venv",
                "created_at": m.get("created_at", ""),
                "complete": complete,
                "default": d.name == default_env,
            }
            if complete or include_incomplete:
                result.append(item)
        except Exception as exc:
            if include_incomplete:
                result.append({"name": d.name, "path": str(d), "complete": False, "reason": str(exc)})
    return result


def load_env(name: str) -> dict[str, Any]:
    mp = manifest_path(name)
    if not mp.exists():
        raise RfpyError(f"Environnement RFPY inconnu: {name}")
    m = read_manifest(mp)
    venv = Path(m.get("venv", stack_dir(name) / ".venv"))
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.exists():
        raise RfpyError(f"Environnement incomplet: {name} (Python du venv introuvable)")
    return m


def repository_index_args(cfg: dict[str, Any]) -> list[str]:
    repos = [r for r in cfg.get("repositories", []) if r.get("enabled") and r.get("simple_url")]
    artifact_enabled = bool(cfg.get("artifact", {}).get("enabled", True))
    if not artifact_enabled:
        repos = [r for r in repos if str(r.get("type", "")).lower() == "pypi"]
    if not cfg.get("artifact", {}).get("allow_public_pypi", True):
        repos = [r for r in repos if str(r.get("type", "")).lower() != "pypi"]
    repos.sort(key=lambda r: int(r.get("priority", 500)))
    if not repos:
        return []
    # uv: les --index ont priorité sur --default-index. On garde donc le repo
    # de plus faible priorité en default-index et les autres en index.
    default = repos[-1]
    args = ["--default-index", str(default["simple_url"]).rstrip("/")]
    for repo in repos[:-1]:
        args += ["--index", str(repo["simple_url"]).rstrip("/")]
    return args


def discover_repo_packages(repo: dict[str, Any], cfg: dict[str, Any]) -> list[str]:
    url = str(repo.get("browse_url") or repo.get("simple_url") or "").strip()
    if not url:
        return []
    if not url.endswith("/"):
        url += "/"
    body = http_get_text(url, timeout=20, cfg=cfg)
    names: dict[str, str] = {}
    for href, label in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body, flags=re.I | re.S):
        label = re.sub(r"<[^>]+>", "", label)
        label = html_mod.unescape(label).strip().strip("/")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", label):
            clean = urllib.parse.urlsplit(href).path.rstrip("/").split("/")[-1]
            label = urllib.parse.unquote(clean)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", label):
            continue
        if label.lower() in {"simple", ".."}:
            continue
        key = re.sub(r"[-_.]+", "-", label.lower())
        names.setdefault(key, label)
    return sorted(names.values(), key=str.lower)


MSVC_BUILD_ERROR_RE = re.compile(r"Microsoft Visual C\+\+ 14(?:\.0)? or greater is required", re.I)
FAILED_BUILD_RE = re.compile(r"Failed to build\s+[`'\"]([^`'\"]+)[`'\"]", re.I)


def _failed_build_requirement(lines: list[str]) -> str:
    for line in reversed(lines):
        m = FAILED_BUILD_RE.search(line)
        if m:
            return m.group(1).strip()
    return ""


def _requirement_name(value: str) -> str:
    try:
        return Requirement(value).name
    except Exception:
        return re.split(r"[<>=!~ @\[]", value, maxsplit=1)[0].strip()


def install_packages(venv_python: Path, packages: list[str], cfg: dict[str, Any], log: Callable[[str], None], label: str) -> None:
    if not packages:
        return
    index_args = repository_index_args(cfg)
    fallback_enabled = bool((cfg.get("package_install", {}) or {}).get("binary_fallback_on_msvc_error", True))
    for start in range(0, len(packages), 50):
        batch = packages[start:start + 50]
        log(f"[...] {label}: {start + 1}-{min(start + len(batch), len(packages))}/{len(packages)}")
        cmd = [uv_path(), "pip", "install", "--python", str(venv_python), *index_args, *batch]
        rc, lines = run_process(cmd, check=False, cfg=cfg, on_line=log)
        if rc == 0:
            continue
        combined = "\n".join(lines)
        failed_req = _failed_build_requirement(lines)
        if fallback_enabled and failed_req and MSVC_BUILD_ERROR_RE.search(combined):
            failed_name = _requirement_name(failed_req)
            log(f"[WARN] Build natif MSVC requis pour {failed_req}. Tentative avec un wheel binaire uniquement.")
            retry = [uv_path(), "pip", "install", "--python", str(venv_python), *index_args, "--only-binary", failed_name, failed_req]
            retry_rc, retry_lines = run_process(retry, check=False, cfg=cfg, on_line=log)
            if retry_rc == 0:
                log(f"[OK] Wheel binaire installé pour {failed_req}; reprise de l'installation initiale.")
                rc, lines = run_process(cmd, check=False, cfg=cfg, on_line=log)
                if rc == 0:
                    continue
            else:
                raise RfpyError(
                    f"{failed_req} nécessite une compilation native, et aucun wheel binaire compatible n'a pu être installé. "
                    "Utilisez une version Python pour laquelle le package publie un wheel, ou installez explicitement les outils de compilation Visual C++."
                )
        raise RfpyError(f"Commande en échec ({rc}): {' '.join(cmd)}")


def post_install_package_runtime(venv_python: Path, packages: list[str], cfg: dict[str, Any], log: Callable[[str], None]) -> None:
    names={canonicalize_name(re.split(r"[<>=!~ @\[]", str(x), maxsplit=1)[0]) for x in packages if str(x).strip()}
    if "robotframework-browser" in names or "robotframework-browser-batteries" in names:
        venv=venv_python.parent.parent if os.name=="nt" else venv_python.parent.parent
        rfbrowser=venv/("Scripts/rfbrowser.exe" if os.name=="nt" else "bin/rfbrowser")
        if rfbrowser.exists():
            log("[...] Installation / vérification de Chromium pour Browser Library")
            run_process([str(rfbrowser),"install","chromium"],cfg=cfg,on_line=log)


def detect_package_version(venv_python: Path, package: str) -> str:
    code = (
        "import importlib.metadata as m; "
        f"print(m.version({package!r}))"
    )
    rc, lines = run_process([str(venv_python), "-c", code], capture=True, check=False)
    return lines[-1].strip() if rc == 0 and lines else ""


def normalize_environment_type(value: str | None) -> str:
    value = (value or "shared").strip().lower()
    aliases = {"projet": "project", "specific": "project", "specifique": "project", "partage": "shared", "global": "shared"}
    value = aliases.get(value, value)
    if value not in {"project", "shared"}:
        raise RfpyError("Type d'environnement invalide. Utiliser 'project' ou 'shared'.")
    return value


def project_venv_path(project_path: str | Path) -> Path:
    p = Path(project_path).expanduser()
    if not p.is_absolute():
        p = p.resolve()
    return p / ".venv"


def python_executable(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def read_python_version(python: Path) -> str:
    rc, lines = run_process([str(python), "-c", "import sys; print('.'.join(map(str,sys.version_info[:3])))"], capture=True, check=False)
    if rc or not lines:
        raise RfpyError(f"Impossible de lire la version Python: {python}")
    return lines[-1].strip()


def normalized_path_key(path: str | Path) -> str:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = p.resolve()
    try:
        p = p.resolve(strict=False)
    except Exception:
        pass
    return os.path.normcase(os.path.normpath(str(p)))


def project_path_owner(project_path: str | Path, exclude_name: str = "") -> str:
    if not str(project_path).strip():
        return ""
    wanted = normalized_path_key(project_path)
    for item in list_envs(include_incomplete=True):
        name = str(item.get("name") or "")
        if exclude_name and name.lower() == exclude_name.lower():
            continue
        mp = stack_dir(name) / "rfpy.json"
        if not mp.exists():
            continue
        with contextlib.suppress(Exception):
            m = read_manifest(mp)
            existing = str(m.get("project_path") or "").strip()
            if existing and normalized_path_key(existing) == wanted:
                return name
    return ""


def assert_project_path_available(project_path: str | Path, exclude_name: str = "") -> None:
    owner = project_path_owner(project_path, exclude_name=exclude_name)
    if owner:
        raise RfpyError(f"Ce dossier projet est déjà associé à l'environnement RFPY '{owner}'.")



def filesystem_roots() -> dict[str, Any]:
    """Return useful roots/favourites for the integrated Web folder browser."""
    favourites: list[dict[str, str]] = []
    home = Path.home()

    def add(label: str, path: Path) -> None:
        try:
            p = path.expanduser()
            if p.exists() and p.is_dir():
                value = str(p)
                if not any(x["path"] == value for x in favourites):
                    favourites.append({"label": label, "path": value})
        except Exception:
            pass

    add("Home", home)
    add("Documents", home / "Documents")
    add("Desktop", home / "Desktop")

    roots: list[dict[str, str]] = []
    if os.name == "nt":
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            p = Path(f"{letter}:\\")
            try:
                if p.exists():
                    roots.append({"label": f"{letter}:\\", "path": str(p)})
            except Exception:
                pass
    else:
        roots.append({"label": "/", "path": "/"})

    default_path = str(home if home.exists() else Path(roots[0]["path"]))
    return {"roots": roots, "favourites": favourites, "default": default_path}


def filesystem_list(path: str) -> dict[str, Any]:
    """List one filesystem directory for the integrated Web browser."""
    if not str(path).strip():
        path = filesystem_roots()["default"]
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = p.resolve()
    try:
        p = p.resolve(strict=False)
    except Exception:
        pass
    if not p.exists():
        raise RfpyError(f"Dossier introuvable: {p}")
    if not p.is_dir():
        raise RfpyError(f"Ce chemin n'est pas un dossier: {p}")

    directories: list[dict[str, str]] = []
    try:
        for child in p.iterdir():
            try:
                if child.is_dir():
                    directories.append({"name": child.name, "path": str(child)})
            except (PermissionError, OSError):
                continue
    except PermissionError as exc:
        raise RfpyError(f"Accès refusé: {p}") from exc
    directories.sort(key=lambda x: x["name"].lower())

    parent = ""
    try:
        if p.parent != p:
            parent = str(p.parent)
    except Exception:
        pass

    return {
        "path": str(p),
        "parent": parent,
        "directories": directories,
    }


def filesystem_mkdir(parent: str, name: str) -> dict[str, str]:
    """Create a folder from the integrated Web browser."""
    clean = str(name).strip()
    if not clean or clean in {".", ".."} or any(ch in clean for ch in '<>:"/\\|?*'):
        raise RfpyError("Nom de dossier invalide.")
    base = Path(parent).expanduser()
    if not base.is_absolute():
        base = base.resolve()
    if not base.exists() or not base.is_dir():
        raise RfpyError(f"Dossier parent introuvable: {base}")
    target = base / clean
    target.mkdir(exist_ok=False)
    return {"path": str(target)}


def save_uploaded_ca(filename: str, data_base64: str) -> str:
    """Store a certificate selected by Chrome under RFPY's managed config."""
    safe_name = Path(str(filename)).name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in {".pem", ".crt", ".cer"}:
        raise RfpyError("Le certificat doit être un fichier .pem, .crt ou .cer.")
    if not data_base64:
        raise RfpyError("Fichier certificat vide.")
    try:
        raw = base64.b64decode(data_base64, validate=True)
    except Exception as exc:
        raise RfpyError("Contenu certificat Base64 invalide.") from exc
    if not raw or len(raw) > 1_000_000:
        raise RfpyError("Certificat vide ou trop volumineux (1 Mo maximum).")

    ca_dir = CONFIG_DIR / "ca"
    ca_dir.mkdir(parents=True, exist_ok=True)
    target = ca_dir / safe_name
    stem, ext = target.stem, target.suffix
    index = 2
    while target.exists() and target.read_bytes() != raw:
        target = ca_dir / f"{stem}-{index}{ext}"
        index += 1
    target.write_bytes(raw)
    return str(target)


def open_local_path(path: str | Path) -> None:
    p = Path(path)
    if not p.exists():
        raise RfpyError(f"Fichier introuvable: {p}")
    devnull = subprocess.DEVNULL
    if os.name == "nt":
        # ShellExecute via a detached helper prevents GUI applications such as
        # VS Code/Electron from writing their own stdout/stderr into `rfpy web`.
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        subprocess.Popen(
            [sys.executable, "-c", "import os,sys; os.startfile(sys.argv[1])", str(p)],
            stdin=devnull, stdout=devnull, stderr=devnull,
            creationflags=creationflags, close_fds=True,
        )
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(p)], stdin=devnull, stdout=devnull, stderr=devnull, start_new_session=True)
    else:
        subprocess.Popen(["xdg-open", str(p)], stdin=devnull, stdout=devnull, stderr=devnull, start_new_session=True)


def probe_project(project_path: str) -> dict[str, Any]:
    if not project_path.strip():
        return {"path": "", "exists": False, "pyproject": False, "uv_lock": False, "venv": False, "python": ""}
    p = Path(project_path).expanduser()
    if not p.is_absolute():
        p = p.resolve()
    venv = p / ".venv"
    py = python_executable(venv)
    version = ""
    if py.exists():
        with contextlib.suppress(Exception):
            version = read_python_version(py)
    return {
        "path": str(p),
        "exists": p.exists(),
        "pyproject": (p / "pyproject.toml").exists(),
        "uv_lock": (p / "uv.lock").exists(),
        "venv": py.exists(),
        "python": version,
    }


def install_environment(
    name: str,
    python_version: str,
    robot_version: str,
    profile: str,
    browser: str = "chromium",
    log: Callable[[str], None] = print,
    environment_type: str = "shared",
    project_path: str = "",
    existing_action: str = "use",
    installation_profile: str = "",
) -> dict[str, Any]:
    cfg = load_config()
    name = normalize_name(name)
    profile = profile.lower().strip()
    if profile not in {"python", "robot", "playwright", "selenium"}:
        raise RfpyError(f"Profil inconnu: {profile}")
    env_type = normalize_environment_type(environment_type)
    existing_action = (existing_action or "use").strip().lower()
    if existing_action not in {"use", "recreate", "fail"}:
        raise RfpyError("Stratégie .venv invalide: use, recreate ou fail.")

    target = stack_dir(name)  # répertoire de métadonnées RFPY dans les deux modes
    if target.exists():
        complete = False
        mp = target / "rfpy.json"
        if mp.exists():
            with contextlib.suppress(Exception):
                old_manifest = read_manifest(mp)
                old_venv = Path(old_manifest.get("venv", target / ".venv"))
                complete = python_executable(old_venv).exists()
        if complete:
            raise RfpyError(f"Un environnement existe déjà: {name}")
        log(f"[INFO] Nettoyage automatique des métadonnées incomplètes: {target}")
        shutil.rmtree(target)

    project = None
    if env_type == "project" and project_path.strip():
        project = Path(project_path).expanduser()
        if not project.is_absolute():
            project = project.resolve()
        assert_project_path_available(project, exclude_name=name)
        project.mkdir(parents=True, exist_ok=True)
        venv = project / ".venv"
    else:
        # Un environnement Projet peut être préparé avant que le dossier du
        # projet n existe. Il reste alors dans RFPY jusqu à son association.
        venv = target / ".venv"

    started = time.monotonic()
    venv_existed_before = venv.exists()
    target.mkdir(parents=True, exist_ok=False)
    venv_owned_by_rfpy = False
    try:
        venv_py = python_executable(venv)
        if env_type == "project" and project is not None and venv_py.exists() and existing_action == "use":
            resolved_python = read_python_version(venv_py)
            requested = (python_version or "").strip()
            if requested and requested not in {"latest", resolved_python} and not resolved_python.startswith(requested + "."):
                log(f"[WARN] .venv existant conservé: Python {resolved_python}; demande RFPY {requested} non appliquée. Utiliser 'recreate' pour le recréer.")
            log(f"[OK] .venv projet existant adopté: {venv} (Python {resolved_python})")
            venv_owned_by_rfpy = False
        else:
            if env_type == "project" and project is not None and venv.exists():
                if existing_action == "fail":
                    raise RfpyError(f"Un .venv existe déjà dans le projet: {venv}")
                if existing_action == "recreate":
                    log(f"[...] Suppression du .venv projet existant: {venv}")
                    shutil.rmtree(venv)
            if not python_version.strip():
                raise RfpyError("Version Python manquante.")
            resolved_python, py_runtime = ensure_python(python_version, log)
            log(f"[...] Création du venv {'projet' if env_type == 'project' else 'partagé'}: {venv}")
            uv_args = [uv_path(), "venv", str(venv), "--python", str(py_runtime), "--relocatable"]
            run_process(uv_args, cfg=cfg, on_line=log)
            venv_py = python_executable(venv)
            venv_owned_by_rfpy = True

        install_packages(venv_py, ["pip", "setuptools", "wheel"], cfg, log, "Outils de base")

        robot_resolved = ""
        robot_version = (robot_version or "").strip()
        if profile != "python":
            if not robot_version:
                raise RfpyError(
                    "Une version Robot Framework est requise pour les profils robot/playwright/selenium. "
                    "Choisissez une version, 'latest', ou utilisez le profil python."
                )
            robot_req = "robotframework" if robot_version == "latest" else f"robotframework=={robot_version}"
            install_packages(venv_py, [robot_req], cfg, log, "Robot Framework")
            robot_resolved = detect_package_version(venv_py, "robotframework")

        if profile == "playwright":
            install_packages(venv_py, ["robotframework-browser", "robotframework-browser-batteries"], cfg, log, "Browser Library")
            rfbrowser = venv / ("Scripts/rfbrowser.exe" if os.name == "nt" else "bin/rfbrowser")
            if not rfbrowser.exists():
                raise RfpyError(f"rfbrowser introuvable après installation: {rfbrowser}")
            last_pct = -1
            def pw_log(line: str) -> None:
                nonlocal last_pct
                m = re.search(r"(\d{1,3})%\s+of\s+([0-9.,]+\s*(?:KiB|MiB|GiB|KB|MB|GB))", line)
                if m:
                    pct = int(m.group(1))
                    if pct != last_pct:
                        last_pct = pct
                        log(f"[PW] Chromium: {pct:3d}% de {m.group(2)}")
                elif re.search(r"(?i)(error:|failed to install|download failure)", line):
                    log(line)
            log("[...] Installation de Chromium Playwright")
            run_process([str(rfbrowser), "install", browser or "chromium"], cfg=cfg, on_line=pw_log)
        elif profile == "selenium":
            install_packages(venv_py, ["robotframework-seleniumlibrary", "selenium"], cfg, log, "Selenium")

        installation_profile = (installation_profile or "").strip()
        if installation_profile:
            profiles = cfg.get("installation_profiles", {}) or {}
            selected_profile = profiles.get(installation_profile)
            if selected_profile is None:
                raise RfpyError(f"Profil d'installation inconnu: {installation_profile}")
            profile_packages=[str(x) for x in selected_profile]
            install_packages(venv_py, profile_packages, cfg, log, f"Profil {installation_profile}")
            post_install_package_runtime(venv_py, profile_packages, cfg, log)
            run_profile_actions(installation_profile, cfg, log)

        if cfg.get("artifact", {}).get("enabled", True):
            for repo in cfg.get("repositories", []):
                if not repo.get("enabled") or not repo.get("install_all"):
                    continue
                log(f"[...] Découverte du dépôt: {repo.get('name', 'repo')}")
                packages = discover_repo_packages(repo, cfg)
                log(f"[OK] {len(packages)} package(s) détecté(s) dans {repo.get('name', 'repo')}")
                try:
                    install_packages(venv_py, packages, cfg, log, f"Dépôt {repo.get('name', 'repo')}")
                except Exception:
                    if repo.get("strict", True):
                        raise
                    log(f"[WARN] Déploiement partiel du dépôt {repo.get('name', 'repo')}")

        manifest = {
            "schema": 2,
            "name": name,
            "created_at": now_iso(),
            "rfpy_version": APP_VERSION,
            "environment_type": env_type,
            "project_path": str(project) if project else "",
            "uv_mode": ("project" if project else "project-pending") if env_type == "project" else "active-venv",
            "profile": profile,
            "python_requested": python_version,
            "python_resolved": resolved_python,
            "robot_requested": robot_version if profile != "python" else "",
            "robot_resolved": robot_resolved,
            "browser": browser if profile == "playwright" else "",
            "installation_profile": installation_profile,
            "stack_dir": str(target),
            "venv": str(venv),
            "venv_owned_by_rfpy": venv_owned_by_rfpy,
            "duration_seconds": round(time.monotonic() - started, 3),
        }
        (target / "rfpy.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        label = "Projet" if env_type == "project" else "Partagé"
        log(f"[OK] Environnement {name} [{label}] prêt en {manifest['duration_seconds']:.1f}s")
        return manifest
    except JobCancelled:
        cleanup = bool((cfg.get("cancellation", {}) or {}).get("cleanup_new_environment", True))
        if cleanup and not venv_existed_before:
            with contextlib.suppress(Exception):
                if venv.exists():
                    shutil.rmtree(venv)
            with contextlib.suppress(Exception):
                if target.exists():
                    shutil.rmtree(target)
            log("[INFO] Installation annulée : nouvel environnement incomplet supprimé.")
        else:
            log("[WARN] Installation annulée : état partiel conservé pour éviter de supprimer un .venv préexistant.")
        raise
    except Exception:
        # Les métadonnées partielles restent pour diagnostic. Pour un Projet,
        # on ne supprime jamais le dossier source. Un .venv déjà adopté n'est
        # jamais supprimé automatiquement en cas d'erreur.
        raise


def set_environment_project_path(name: str, project_path: str) -> dict[str, Any]:
    m = load_env(name)
    if normalize_environment_type(str(m.get("environment_type") or "shared")) != "project":
        raise RfpyError("Seul un environnement de type Projet peut être associé à un dossier projet.")
    project_path = project_path.strip()
    if not project_path:
        raise RfpyError("Dossier projet manquant.")
    project = Path(project_path).expanduser()
    if not project.is_absolute():
        project = project.resolve()
    assert_project_path_available(project, exclude_name=name)
    project.mkdir(parents=True, exist_ok=True)

    old_project = str(m.get("project_path") or "").strip()
    if old_project and normalized_path_key(old_project) == normalized_path_key(project):
        return m
    if os.environ.get("RFPY_ENV", "").lower() == name.lower():
        raise RfpyError("Désactivez cet environnement avant de changer son dossier projet.")

    current_venv = Path(str(m.get("venv") or stack_dir(name) / ".venv"))
    target_venv = project / ".venv"
    if target_venv.exists() and normalized_path_key(target_venv) != normalized_path_key(current_venv):
        raise RfpyError(f"Le dossier cible contient déjà un .venv: {target_venv}")

    owned = bool(m.get("venv_owned_by_rfpy", True))
    if old_project and not owned:
        raise RfpyError("Ce venv projet a été adopté et n'est pas géré par RFPY. Le dossier projet ne peut pas être déplacé automatiquement.")

    if normalized_path_key(current_venv) != normalized_path_key(target_venv):
        if not current_venv.exists():
            raise RfpyError(f"Venv source introuvable: {current_venv}")
        target_venv.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(current_venv), str(target_venv))

    m["project_path"] = str(project)
    m["venv"] = str(target_venv)
    m["uv_mode"] = "project"
    m["venv_owned_by_rfpy"] = owned
    manifest_path(name).write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return m



def set_environment_type(name: str, environment_type: str) -> dict[str, Any]:
    """Change an environment between Project and Shared safely.

    Shared -> Project:
      metadata-only conversion. The existing venv remains where it is and the
      environment becomes project-pending until a project folder is linked.

    Project -> Shared:
      when the project is linked and the .venv is RFPY-owned + relocatable,
      move it back under C:\\RFPY\\stacks\\<name>\\.venv and clear the project link.
      Adopted/external venvs are never moved automatically.
    """
    m = load_env(name)
    current = normalize_environment_type(str(m.get("environment_type") or "shared"))
    target_type = normalize_environment_type(environment_type)
    if current == target_type:
        return m

    current_venv = Path(str(m.get("venv") or stack_dir(name) / ".venv"))
    old_project = str(m.get("project_path") or "").strip()
    owned = bool(m.get("venv_owned_by_rfpy", current == "shared" or not old_project))

    if target_type == "project":
        m["environment_type"] = "project"
        m["project_path"] = ""
        m["uv_mode"] = "project-pending"
        m["venv"] = str(current_venv)
    else:
        target_venv = stack_dir(name) / ".venv"
        if old_project:
            if not owned:
                raise RfpyError(
                    "Ce venv projet a été adopté/externe. Il ne peut pas être "
                    "converti automatiquement en Partagé. Dupliquez-le plutôt "
                    "dans un nouvel environnement Partagé."
                )
            pyvenv = current_venv / "pyvenv.cfg"
            if pyvenv.exists():
                cfg_text = pyvenv.read_text(encoding="utf-8", errors="replace")
                if not re.search(r"(?im)^\s*relocatable\s*=\s*true\s*$", cfg_text):
                    raise RfpyError(
                        "Le .venv projet n'est pas relocatable. "
                        "Dupliquez/recréez l'environnement avant de le convertir."
                    )
            if target_venv.exists() and normalized_path_key(target_venv) != normalized_path_key(current_venv):
                raise RfpyError(f"Le venv cible existe déjà: {target_venv}")
            if normalized_path_key(current_venv) != normalized_path_key(target_venv):
                target_venv.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(current_venv), str(target_venv))
            current_venv = target_venv

        m["environment_type"] = "shared"
        m["project_path"] = ""
        m["uv_mode"] = "active-venv"
        m["venv"] = str(current_venv)
        m["venv_owned_by_rfpy"] = owned

    manifest_path(name).write_text(
        json.dumps(m, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return m


def duplicate_environment(source: str, new_name: str, log: Callable[[str], None] = print) -> dict[str, Any]:
    """Recreate an equivalent venv using uv cache instead of byte-copying it.

    Copying a Windows venv byte-for-byte is unsafe because console launchers can
    contain absolute interpreter paths. RFPY therefore recreates the venv with
    the same Python and package snapshot; uv normally reuses its local cache.
    """
    src = load_env(source)
    new_name = normalize_name(new_name)
    target = stack_dir(new_name)
    if target.exists():
        raise RfpyError(f"Un environnement existe déjà: {new_name}")
    resolved = str(src.get("python_resolved") or "").strip()
    if not resolved:
        raise RfpyError("Version Python source inconnue.")
    _, runtime = ensure_python(resolved, log)
    target.mkdir(parents=True, exist_ok=False)
    venv = target / ".venv"
    try:
        log(f"[...] Création du clone {new_name} avec Python {resolved}")
        run_process([uv_path(), "venv", str(venv), "--python", str(runtime), "--relocatable"], cfg=load_config(), on_line=log)
        py = python_executable(venv)
        freeze = pip_freeze(source)
        cloneable: list[str] = []
        skipped: list[str] = []
        for line in freeze:
            low = line.lower().strip()
            if low.startswith("-e ") or " @ file:" in low or low.startswith("file:"):
                skipped.append(line)
            else:
                cloneable.append(line)
        if cloneable:
            install_packages(py, cloneable, load_config(), log, "Clone des packages")
        if skipped:
            log(f"[WARN] {len(skipped)} dépendance(s) locale(s)/editable non dupliquée(s).")

        profile = str(src.get("profile") or "python")
        if profile == "playwright":
            rfbrowser = venv / ("Scripts/rfbrowser.exe" if os.name == "nt" else "bin/rfbrowser")
            if rfbrowser.exists():
                log("[...] Vérification du navigateur Playwright du clone")
                run_process([str(rfbrowser), "install", str(src.get("browser") or "chromium")], cfg=load_config(), on_line=log)

        m = dict(src)
        m.update({
            "name": new_name,
            "created_at": now_iso(),
            "rfpy_version": APP_VERSION,
            "stack_dir": str(target),
            "venv": str(venv),
            "venv_owned_by_rfpy": True,
            "project_path": "",
            "uv_mode": "project-pending" if normalize_environment_type(str(src.get("environment_type") or "shared")) == "project" else "active-venv",
            "duplicated_from": source,
        })
        manifest_path(new_name).write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        log(f"[OK] Environnement dupliqué: {source} -> {new_name}")
        return m
    except Exception:
        # Conserver la pile partielle pour diagnostic, comme les installations.
        raise


def delete_environment(name: str, log: Callable[[str], None] = print) -> None:
    target = stack_dir(name)
    if not target.exists():
        raise RfpyError(f"Environnement inconnu: {name}")
    m = read_manifest(target / "rfpy.json") if (target / "rfpy.json").exists() else {}
    env_type = normalize_environment_type(str(m.get("environment_type") or "shared"))
    venv = Path(m.get("venv", target / ".venv"))
    owned = bool(m.get("venv_owned_by_rfpy", env_type == "shared"))
    log(f"[...] Suppression de {name} ({'Projet' if env_type == 'project' else 'Partagé'})")
    started = time.monotonic()
    if env_type == "project":
        project = Path(str(m.get("project_path") or "")) if m.get("project_path") else None
        expected = (project / ".venv") if project else None
        # Sécurité : RFPY ne supprime jamais les sources du projet. Le .venv
        # n'est supprimé que s'il a été créé/recréé par RFPY et correspond bien
        # à <projet>/.venv. Un venv adopté reste intact.
        if owned and expected and venv == expected and venv.exists():
            log(f"[...] Suppression du .venv géré par RFPY: {venv}")
            shutil.rmtree(venv)
        elif venv.exists():
            log(f"[INFO] .venv conservé (adopté/externe): {venv}")
        shutil.rmtree(target)
    else:
        shutil.rmtree(target)
    cfg = load_config()
    if cfg.get("default_environment") == name:
        cfg["default_environment"] = ""
        save_config(cfg)
    log(f"[OK] Environnement supprimé: {name} ({time.monotonic() - started:.1f}s)")


def rename_environment(old: str, new: str) -> dict[str, Any]:
    old = normalize_name(old)
    new = normalize_name(new)
    src = stack_dir(old)
    dst = stack_dir(new)
    if not src.exists():
        raise RfpyError(f"Environnement inconnu: {old}")
    if dst.exists():
        raise RfpyError(f"Le nom existe déjà: {new}")
    m = load_env(old)
    env_type = normalize_environment_type(str(m.get("environment_type") or "shared"))
    embedded_venv = not str(m.get("project_path") or "").strip() and normalized_path_key(m.get("venv", src / ".venv")) == normalized_path_key(src / ".venv")
    if env_type == "shared" or embedded_venv:
        pyvenv = Path(m["venv"]) / "pyvenv.cfg"
        if pyvenv.exists():
            cfg_text = pyvenv.read_text(encoding="utf-8", errors="replace")
            if not re.search(r"(?im)^\s*relocatable\s*=\s*true\s*$", cfg_text):
                raise RfpyError("Le venv n'est pas relocatable. Recréez-le avec RFPY avant de le renommer.")
        shutil.move(str(src), str(dst))
        mp = dst / "rfpy.json"
        m = read_manifest(mp)
        m["name"] = new
        m["stack_dir"] = str(dst)
        m["venv"] = str(dst / ".venv")
    else:
        # Pour un Projet, renommer RFPY ne renomme jamais le dossier source.
        # Seul l'enregistrement/métadonnée RFPY change de nom.
        shutil.move(str(src), str(dst))
        mp = dst / "rfpy.json"
        m = read_manifest(mp)
        m["name"] = new
        m["stack_dir"] = str(dst)
    mp.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    cfg = load_config()
    if cfg.get("default_environment") == old:
        cfg["default_environment"] = new
        save_config(cfg)
    return m


def set_default_environment(name: str) -> None:
    load_env(name)
    cfg = load_config()
    cfg["default_environment"] = name
    save_config(cfg)


def installed_packages(name: str) -> list[dict[str, str]]:
    m = load_env(name)
    py = Path(m["venv"]) / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    rc, lines = run_process([str(py), "-m", "pip", "list", "--format", "json"], capture=True, check=False)
    if rc == 0:
        try:
            return json.loads("\n".join(lines))
        except Exception:
            pass
    rc, lines = run_process([uv_path(), "pip", "list", "--python", str(py), "--format", "json"], capture=True, check=False)
    if rc == 0:
        try:
            return json.loads("\n".join(lines))
        except Exception:
            pass
    return []



def uv_info() -> dict[str,str]:
    try:
        rc,lines=run_process([uv_path(),"--version"],capture=True,check=False)
        raw=" ".join(lines).strip(); m=re.search(r"\buv\s+([0-9][^\s]*)",raw)
        return {"path":uv_path(),"version":m.group(1) if m else raw,"scope":"RFPY global"}
    except Exception as exc:
        return {"path":"","version":"","scope":f"indisponible: {exc}"}

def pip_freeze(name: str) -> list[str]:
    m=load_env(name); py=Path(m["venv"])/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    rc,lines=run_process([str(py),"-m","pip","freeze"],capture=True,check=False)
    if rc: rc,lines=run_process([uv_path(),"pip","freeze","--python",str(py)],capture=True,check=False)
    return [x for x in lines if x.strip()] if rc==0 else []

def parse_profile_dependency_file(filename: str, content: str) -> dict[str, Any]:
    """Extract installable dependencies from requirements.txt or pyproject.toml."""
    safe_name = Path(str(filename)).name
    content = content.lstrip("\ufeff")
    lower = safe_name.lower()
    packages: list[str] = []
    warnings: list[str] = []
    if lower.endswith(".toml"):
        try:
            data = tomllib.loads(content)
        except Exception as exc:
            raise RfpyError(f"pyproject.toml invalide: {exc}") from exc
        project = data.get("project") or {}
        raw_deps = project.get("dependencies") or []
        if not isinstance(raw_deps, list):
            raise RfpyError("[project].dependencies doit être une liste.")
        for raw in raw_deps:
            value = str(raw).strip()
            if not value:
                continue
            try:
                Requirement(value)
            except Exception:
                warnings.append(f"Dépendance ignorée: {value}")
                continue
            if value not in packages:
                packages.append(value)
        optional = project.get("optional-dependencies") or {}
        if optional:
            warnings.append("Les dépendances optionnelles [project.optional-dependencies] ne sont pas importées automatiquement.")
    elif lower.endswith(".txt"):
        logical: list[str] = []
        pending = ""
        for raw in content.splitlines():
            line = raw.strip()
            if pending:
                line = pending + line
                pending = ""
            if line.endswith("\\"):
                pending = line[:-1].rstrip() + " "
                continue
            logical.append(line)
        if pending:
            logical.append(pending.strip())
        for line in logical:
            if not line or line.startswith("#"):
                continue
            if " #" in line:
                line = line.split(" #", 1)[0].rstrip()
            low = line.lower()
            if low.startswith(("-r ", "--requirement ", "-c ", "--constraint ", "-e ", "--editable ", "--index-url", "--extra-index-url", "--find-links", "--trusted-host")):
                warnings.append(f"Directive non importée: {line}")
                continue
            try:
                Requirement(line)
            except Exception:
                warnings.append(f"Dépendance ignorée: {line}")
                continue
            if line not in packages:
                packages.append(line)
    else:
        raise RfpyError("Formats acceptés: requirements.txt ou pyproject.toml.")
    if not packages:
        raise RfpyError("Aucune dépendance installable trouvée dans le fichier.")
    suggested = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(safe_name).stem).strip("-._") or "Profil importé"
    return {"packages": packages, "warnings": warnings, "suggested_name": suggested}


def env_details(name: str) -> dict[str,Any]:
    m=load_env(name); env_type=normalize_environment_type(str(m.get("environment_type") or "shared"))
    packages=installed_packages(name)
    names={canonicalize_name(str(p.get("name") or "")) for p in packages}
    if "robotframework-browser" in names:
        test_kind="playwright"
    elif "robotframework-seleniumlibrary" in names and "selenium" in names:
        test_kind="selenium"
    elif "robotframework" in names:
        test_kind="robot"
    else:
        test_kind="python"
    linked=bool(str(m.get("project_path") or "").strip())
    lang=current_language()
    notes={
        "fr": {"linked":"uv utilise le projet lié et son .venv (UV_PROJECT).","pending":"Projet non encore lié : le venv reste sous RFPY et les commandes uv de projet sont protégées.","shared":"uv pip cible le venv actif ; les commandes de projet uv sont protégées par le shim RFPY."},
        "en": {"linked":"uv uses the linked project and its .venv (UV_PROJECT).","pending":"Project not linked yet: the venv stays under RFPY and uv project commands are protected.","shared":"uv pip targets the active venv; uv project commands are protected by the RFPY shim."},
        "de": {"linked":"uv verwendet das verknüpfte Projekt und dessen .venv (UV_PROJECT).","pending":"Projekt noch nicht verknüpft: Das venv bleibt unter RFPY und uv-Projektbefehle sind geschützt.","shared":"uv pip verwendet das aktive venv; uv-Projektbefehle werden durch den RFPY-Shim geschützt."},
        "es": {"linked":"uv usa el proyecto vinculado y su .venv (UV_PROJECT).","pending":"Proyecto aún no vinculado: el venv permanece en RFPY y los comandos de proyecto de uv están protegidos.","shared":"uv pip usa el venv activo; los comandos de proyecto de uv están protegidos por el shim de RFPY."},
        "zh": {"linked":"uv 使用已关联项目及其 .venv（UV_PROJECT）。","pending":"项目尚未关联：venv 保留在 RFPY 下，uv 项目命令受到保护。","shared":"uv pip 使用当前活动 venv；uv 项目命令由 RFPY shim 保护。"},
    }
    bucket=notes.get(lang,notes["en"])
    note=bucket["linked" if env_type=="project" and linked else "pending" if env_type=="project" else "shared"]
    return {"manifest":m,"packages":packages,"freeze":pip_freeze(name),"uv":uv_info(),"note":note,"test_kind":test_kind}

def python_distributions(name: str) -> list[dict[str,Any]]:
    m=load_env(name); py=Path(m["venv"])/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    code="import importlib.metadata as md,json\nfor d in md.distributions():\n n=d.metadata.get('Name') or ''\n if n: print(json.dumps({'name':n,'version':d.version,'requires_python':d.metadata.get('Requires-Python') or '','requires':d.requires or []},ensure_ascii=False))"
    rc,lines=run_process([str(py),"-c",code],capture=True,check=False); out=[]
    if rc==0:
        for line in lines:
            try:
                o=json.loads(line)
                if o.get("name") and o.get("version"): out.append(o)
            except Exception: pass
    return out

def npm_components_for_env(name: str) -> list[dict[str,str]]:
    m=load_env(name); venv=Path(m["venv"])
    roots=list(venv.glob("Lib/site-packages/BrowserBatteries/bin/wrapper/node_modules")) if os.name=="nt" else list(venv.glob("lib/python*/site-packages/BrowserBatteries/bin/wrapper/node_modules"))
    out={}
    for root in roots:
        for pkg in root.rglob("package.json") if root.exists() else []:
            try:
                d=json.loads(pkg.read_text(encoding="utf-8",errors="replace")); n=str(d.get("name") or "").strip(); v=str(d.get("version") or "").strip()
                if n and v:
                    p=f"pkg:npm/{urllib.parse.quote(n,safe='/')}@{v}"; out[p]={"name":n,"version":v,"purl":p,"path":str(pkg.parent)}
            except Exception: pass
    return list(out.values())

def generate_sbom(name: str) -> Path:
    m=load_env(name); dists=python_distributions(name); comps=[]; refs={}; depmap={}
    for d in dists:
        norm=canonicalize_name(d["name"]); p=f"pkg:pypi/{urllib.parse.quote(norm)}@{d['version']}"; refs[norm]=p; props=[]
        if d.get("requires_python"): props.append({"name":"rfpy:requires_python","value":d["requires_python"]})
        comps.append({"type":"library","name":d["name"],"version":d["version"],"bom-ref":p,"purl":p,"properties":props})
    for d in dists:
        src=refs.get(canonicalize_name(d["name"])); deps=[]
        for raw in d.get("requires") or []:
            try:
                req=Requirement(raw); ref=refs.get(canonicalize_name(req.name))
                if ref: deps.append(ref)
            except Exception: pass
        if src: depmap[src]=sorted(set(deps))
    for n in npm_components_for_env(name): comps.append({"type":"library","name":n["name"],"version":n["version"],"bom-ref":n["purl"],"purl":n["purl"],"properties":[{"name":"rfpy:path","value":n["path"]}]})
    pyv=str(m.get("python_resolved") or "unknown"); pyref=f"pkg:generic/cpython@{pyv}"; comps.append({"type":"application","name":"CPython","version":pyv,"bom-ref":pyref,"purl":pyref})
    u=uv_info(); uvv=u.get("version") or "unknown"; uvref=f"pkg:generic/uv@{uvv}"; comps.append({"type":"application","name":"uv","version":uvv,"bom-ref":uvref,"purl":uvref,"properties":[{"name":"rfpy:scope","value":"global manager"},{"name":"rfpy:path","value":u.get("path","")}]})
    root=f"rfpy:{name}"; deps=[{"ref":root,"dependsOn":[c["bom-ref"] for c in comps]}]+[{"ref":k,"dependsOn":v} for k,v in depmap.items()]
    bom={"bomFormat":"CycloneDX","specVersion":"1.6","serialNumber":"urn:uuid:"+str(uuid.uuid4()),"version":1,"metadata":{"timestamp":now_iso(),"authors":[{"name":AUTHOR}],"tools":{"components":[{"type":"application","name":"RFPY","version":APP_VERSION,"authors":[{"name":AUTHOR}],"licenses":[{"license":{"id":LICENSE_ID}}]}]},"component":{"type":"application","name":"RFPY environment","version":name,"bom-ref":root}},"components":comps,"dependencies":deps}
    reports=stack_dir(name)/"reports"; reports.mkdir(parents=True,exist_ok=True); path=reports/f"rfpy-{name}.cdx.json"; path.write_text(json.dumps(bom,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); return path

def export_requirements(name: str) -> Path:
    p=stack_dir(name)/"requirements.txt"; p.write_text("\n".join(pip_freeze(name))+"\n",encoding="utf-8"); return p

def export_pyproject(name: str) -> Path:
    m=load_env(name); pkgs=installed_packages(name); deps=[f'{x["name"]}=={x["version"]}' for x in pkgs if canonicalize_name(x["name"]) not in {"pip","setuptools","wheel"}]; pyv=str(m.get("python_resolved") or ""); parts=pyv.split("."); req=""
    if len(parts)>=2 and parts[0].isdigit() and parts[1].isdigit(): req=f">={parts[0]}.{parts[1]},<{parts[0]}.{int(parts[1])+1}"
    lines=["[project]",f'name = "rfpy-{normalize_name(name).lower()}"','version = "0.0.0"']
    if req: lines.append(f'requires-python = "{req}"')
    lines += ["dependencies = ["]+[f"  {json.dumps(x)}," for x in sorted(deps,key=str.lower)]+["]","","[tool.rfpy]",f"environment = {json.dumps(name)}",f"profile = {json.dumps(str(m.get('profile') or ''))}",f"generated-at = {json.dumps(now_iso())}"]
    p=stack_dir(name)/"pyproject.toml"; p.write_text("\n".join(lines)+"\n",encoding="utf-8"); return p

def install_selected_packages(name: str, packages: list[str], log: Callable[[str],None]=print, profile_name: str = "") -> dict[str,Any]:
    clean=[]
    for x in packages:
        x=str(x).strip()
        if x and x not in clean: clean.append(x)
    if not clean: raise RfpyError("Aucun package sélectionné.")
    m=load_env(name)
    py=Path(m["venv"])/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    cfg=load_config()
    try:
        install_packages(py,clean,cfg,log,"Packages sélectionnés")
        post_install_package_runtime(py,clean,cfg,log)
    except JobCancelled:
        log("[WARN] Arrêt demandé. Les modifications déjà appliquées à cet environnement existant sont conservées; aucun rollback automatique n'est effectué.")
        raise
    selected_profile=(profile_name or "").strip()
    if selected_profile:
        profiles=cfg.get("installation_profiles", {}) or {}
        if selected_profile not in profiles:
            raise RfpyError(f"Profil d'installation inconnu: {selected_profile}")
        run_profile_actions(selected_profile,cfg,log)
    return {"environment":name,"installed":clean,"profile":selected_profile}

def run_smoke_test(name: str, url: str="https://www.google.com", headless: bool=True, log: Callable[[str],None]=print) -> dict[str,Any]:
    m=load_env(name); py=Path(m["venv"])/("Scripts/python.exe" if os.name=="nt" else "bin/python"); work=stack_dir(name)/"reports"/"smoke"; work.mkdir(parents=True,exist_ok=True)
    packages={canonicalize_name(str(p.get("name") or "")) for p in installed_packages(name)}
    if "robotframework-browser" in packages:
        kind="playwright"
    elif "robotframework-seleniumlibrary" in packages and "selenium" in packages:
        kind="selenium"
    elif "robotframework" in packages:
        kind="robot"
    else:
        kind="python"
    if kind=="python":
        rc,lines=run_process([str(py),"-c",'import sys,ssl,json,venv; print("Python",sys.version.split()[0]); print("ssl",ssl.OPENSSL_VERSION); print("RFPY smoke OK")'],capture=True,check=False)
    else:
        suite=work/"rfpy_smoke.robot"
        if kind=="playwright":
            h="True" if headless else "False"
            body=f"*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\nRFPY Playwright Smoke\n    New Browser    chromium    headless={h}\n    New Page    {url}\n    ${{title}}=    Get Title\n    Log    ${{title}}\n    Close Browser\n"
        elif kind=="selenium":
            options="    options=add_argument(\"--headless=new\")" if headless else ""
            body=f"*** Settings ***\nLibrary    SeleniumLibrary\n\n*** Test Cases ***\nRFPY Selenium Smoke\n    Open Browser    {url}    chrome{options}\n    ${{title}}=    Get Title\n    Log    ${{title}}\n    Close All Browsers\n"
        else:
            body="*** Test Cases ***\nRFPY Robot Smoke\n    Log    RFPY Robot Framework smoke OK\n"
        suite.write_text(body,encoding="utf-8"); rc,lines=run_process([str(py),"-m","robot","--outputdir",str(work),str(suite)],capture=True,check=False)
    for line in lines: log(line)
    if rc: raise RfpyError(f"Smoke test en échec (code={rc}).")
    log("[OK] Smoke test terminé."); return {"environment":name,"kind":kind,"ok":True,"headless":headless}

DOCTOR_I18N = {
    "fr": {
        "priority": "Priorité commandes", "priority_ok": "RFPY/bin précède le venv actif (rfpy/uv non masquables)", "priority_warn": "Le venv actif précède RFPY/bin ; rfpy ou uv peuvent être masqués. Réexécutez l'installeur RFPY puis réactivez l'environnement.",
        "write": "Écriture", "proxy_enabled": "activé", "proxy_disabled": "désactivé", "repo": "Dépôt {name}", "simple_missing": "URL Simple absente",
        "env": "Env {name}", "incomplete": "incomplet : {reason}", "manifest_missing": "manifeste absent", "python_missing": "Python absent", "project": "Projet", "shared": "Partagé", "python_ko": "Python KO",
        "project_name": "Projet {name}", "present": "présent", "absent": "absent", "project_unlinked": "dossier projet non encore associé", "project_pending": "mode project-pending protégé", "uv_project": "uv Projet {name}", "uv_shared": "uv Partagé {name}", "shared_ok": "VIRTUAL_ENV + uv pip ; commandes projet protégées",
        "rfmcp_missing": "package présent, commande robotmcp introuvable", "ollama_missing": "client Python présent, runtime Ollama non détecté", "default_env": "Env par défaut", "default_missing": "{name} n'existe plus", "web_used": "déjà utilisé", "web_available": "disponible", "status": "Statut",
    },
    "en": {
        "priority": "Command priority", "priority_ok": "RFPY/bin precedes the active venv (rfpy/uv cannot be shadowed)", "priority_warn": "The active venv precedes RFPY/bin; rfpy or uv may be shadowed. Run the RFPY installer again, then reactivate the environment.",
        "write": "Write access", "proxy_enabled": "enabled", "proxy_disabled": "disabled", "repo": "Repository {name}", "simple_missing": "Simple URL missing",
        "env": "Env {name}", "incomplete": "incomplete: {reason}", "manifest_missing": "manifest missing", "python_missing": "Python missing", "project": "Project", "shared": "Shared", "python_ko": "Python failed",
        "project_name": "Project {name}", "present": "present", "absent": "absent", "project_unlinked": "project folder not linked yet", "project_pending": "protected project-pending mode", "uv_project": "uv Project {name}", "uv_shared": "uv Shared {name}", "shared_ok": "VIRTUAL_ENV + uv pip; project commands protected",
        "rfmcp_missing": "package present, robotmcp command not found", "ollama_missing": "Python client present, Ollama runtime not detected", "default_env": "Default env", "default_missing": "{name} no longer exists", "web_used": "already in use", "web_available": "available", "status": "Status",
    },
    "de": {
        "priority": "Befehlspriorität", "priority_ok": "RFPY/bin steht vor dem aktiven venv (rfpy/uv können nicht verdeckt werden)", "priority_warn": "Das aktive venv steht vor RFPY/bin; rfpy oder uv können verdeckt werden. Führen Sie den RFPY-Installer erneut aus und aktivieren Sie die Umgebung danach neu.",
        "write": "Schreibzugriff", "proxy_enabled": "aktiviert", "proxy_disabled": "deaktiviert", "repo": "Repository {name}", "simple_missing": "Simple-URL fehlt",
        "env": "Umgebung {name}", "incomplete": "unvollständig: {reason}", "manifest_missing": "Manifest fehlt", "python_missing": "Python fehlt", "project": "Projekt", "shared": "Geteilt", "python_ko": "Python fehlgeschlagen",
        "project_name": "Projekt {name}", "present": "vorhanden", "absent": "fehlt", "project_unlinked": "Projektordner noch nicht verknüpft", "project_pending": "geschützter project-pending-Modus", "uv_project": "uv Projekt {name}", "uv_shared": "uv Geteilt {name}", "shared_ok": "VIRTUAL_ENV + uv pip; Projektbefehle geschützt",
        "rfmcp_missing": "Paket vorhanden, Befehl robotmcp nicht gefunden", "ollama_missing": "Python-Client vorhanden, Ollama-Laufzeit nicht erkannt", "default_env": "Standardumgebung", "default_missing": "{name} existiert nicht mehr", "web_used": "bereits belegt", "web_available": "verfügbar", "status": "Status",
    },
    "es": {
        "priority": "Prioridad de comandos", "priority_ok": "RFPY/bin precede al venv activo (rfpy/uv no pueden quedar ocultos)", "priority_warn": "El venv activo precede a RFPY/bin; rfpy o uv pueden quedar ocultos. Vuelva a ejecutar el instalador RFPY y reactive el entorno.",
        "write": "Escritura", "proxy_enabled": "activado", "proxy_disabled": "desactivado", "repo": "Repositorio {name}", "simple_missing": "Falta la URL Simple",
        "env": "Entorno {name}", "incomplete": "incompleto: {reason}", "manifest_missing": "falta el manifiesto", "python_missing": "falta Python", "project": "Proyecto", "shared": "Compartido", "python_ko": "Python falló",
        "project_name": "Proyecto {name}", "present": "presente", "absent": "ausente", "project_unlinked": "carpeta de proyecto aún no vinculada", "project_pending": "modo project-pending protegido", "uv_project": "uv Proyecto {name}", "uv_shared": "uv Compartido {name}", "shared_ok": "VIRTUAL_ENV + uv pip; comandos de proyecto protegidos",
        "rfmcp_missing": "paquete presente, no se encontró el comando robotmcp", "ollama_missing": "cliente Python presente, runtime Ollama no detectado", "default_env": "Entorno predeterminado", "default_missing": "{name} ya no existe", "web_used": "ya está en uso", "web_available": "disponible", "status": "Estado",
    },
    "zh": {
        "priority": "命令优先级", "priority_ok": "RFPY/bin 位于活动 venv 之前（rfpy/uv 不会被遮蔽）", "priority_warn": "活动 venv 位于 RFPY/bin 之前；rfpy 或 uv 可能被遮蔽。请重新运行 RFPY 安装程序，然后重新激活环境。",
        "write": "写入权限", "proxy_enabled": "已启用", "proxy_disabled": "已禁用", "repo": "仓库 {name}", "simple_missing": "缺少 Simple URL",
        "env": "环境 {name}", "incomplete": "不完整：{reason}", "manifest_missing": "缺少清单", "python_missing": "缺少 Python", "project": "项目", "shared": "共享", "python_ko": "Python 失败",
        "project_name": "项目 {name}", "present": "存在", "absent": "缺失", "project_unlinked": "项目目录尚未关联", "project_pending": "受保护的 project-pending 模式", "uv_project": "uv 项目 {name}", "uv_shared": "uv 共享 {name}", "shared_ok": "VIRTUAL_ENV + uv pip；项目命令受保护",
        "rfmcp_missing": "软件包存在，但找不到 robotmcp 命令", "ollama_missing": "Python 客户端存在，但未检测到 Ollama 运行时", "default_env": "默认环境", "default_missing": "{name} 已不存在", "web_used": "已被占用", "web_available": "可用", "status": "状态",
    },
}


def _doctor_language() -> str:
    lang = current_language()
    return lang if lang in DOCTOR_I18N else "fr"


def doctor() -> dict[str, Any]:
    cfg = load_config()
    lang = _doctor_language()
    t = DOCTOR_I18N[lang]
    checks: list[dict[str, str]] = []

    def dt(key: str, **kwargs: Any) -> str:
        template = str(t.get(key) or DOCTOR_I18N["en"].get(key) or key)
        return template.format(**kwargs)

    def add(level: str, name: str, detail: str) -> None:
        checks.append({"level": level, "name": name, "detail": detail})

    add("ok", "RFPY", f"v{APP_VERSION} - {HOME}")
    if os.environ.get("RFPY_ENV"):
        parts = [p.rstrip("\\/").lower() for p in os.environ.get("PATH", "").split(os.pathsep) if p]
        bin_dir = str(BIN_DIR).rstrip("\\/").lower()
        venv_scripts = str(Path(os.environ.get("RFPY_VENV", "")) / ("Scripts" if os.name == "nt" else "bin")).rstrip("\\/").lower()
        try:
            bin_pos = parts.index(bin_dir)
        except ValueError:
            bin_pos = 999999
        try:
            venv_pos = parts.index(venv_scripts)
        except ValueError:
            venv_pos = 999999
        if bin_pos < venv_pos:
            add("ok", dt("priority"), dt("priority_ok"))
        else:
            add("warn", dt("priority"), dt("priority_warn"))
    try:
        ensure_dirs()
        probe = HOME / f".write-{uuid.uuid4().hex}.tmp"
        probe.write_text("ok", encoding="ascii")
        probe.unlink()
        add("ok", dt("write"), str(HOME))
    except Exception as exc:
        add("error", dt("write"), str(exc))

    try:
        rc, lines = run_process([uv_path(), "--version"], capture=True, check=False)
        add("ok" if rc == 0 else "error", "uv", " ".join(lines[-2:]) or f"code={rc}")
    except Exception as exc:
        add("error", "uv", str(exc))

    path_entries = [p.rstrip("\\/").lower() for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    add("ok" if str(BIN_DIR).rstrip("\\/").lower() in path_entries else "warn", "PATH", str(BIN_DIR))

    proxy = cfg.get("proxy", {})
    add("ok", "Proxy", dt("proxy_enabled") if proxy.get("enabled") else dt("proxy_disabled"))

    for repo in cfg.get("repositories", []):
        if not repo.get("enabled"):
            continue
        url = str(repo.get("simple_url", ""))
        repo_name = dt("repo", name=repo.get("name"))
        if not url:
            add("warn", repo_name, dt("simple_missing"))
            continue
        try:
            http_get_text(url.rstrip("/") + "/", timeout=5, cfg=cfg)
            add("ok", repo_name, url)
        except Exception as exc:
            add("error", repo_name, f"{url} - {exc}")

    complete_names = set()
    for env in list_envs(include_incomplete=True):
        env_name = dt("env", name=env["name"])
        if not env.get("complete"):
            reason = str(env.get("reason", "") or "")
            if reason == "manifest absent":
                reason = dt("manifest_missing")
            elif not reason:
                reason = dt("python_missing")
            add("warn", env_name, dt("incomplete", reason=reason))
            continue
        complete_names.add(env["name"])
        try:
            m = load_env(env["name"])
            py = python_executable(Path(m["venv"]))
            rc, lines = run_process([str(py), "--version"], capture=True, check=False)
            env_type = normalize_environment_type(str(m.get("environment_type") or "shared"))
            detail = f"{dt('project') if env_type == 'project' else dt('shared')} - " + (" ".join(lines[-1:]) or dt("python_ko"))
            add("ok" if rc == 0 else "error", env_name, detail)
            if env_type == "project":
                project_raw = str(m.get("project_path") or "").strip()
                project_label = dt("project_name", name=env["name"])
                if project_raw:
                    project = Path(project_raw)
                    add("ok" if project.exists() else "error", project_label, str(project))
                    add("ok" if (project / "pyproject.toml").exists() else "warn", f"pyproject {env['name']}", dt("present") if (project / "pyproject.toml").exists() else dt("absent"))
                    add("ok" if (project / "uv.lock").exists() else "warn", f"uv.lock {env['name']}", dt("present") if (project / "uv.lock").exists() else dt("absent"))
                    expected = project / ".venv"
                    add("ok" if normalized_path_key(m["venv"]) == normalized_path_key(expected) else "error", dt("uv_project", name=env["name"]), f".venv={m['venv']}")
                else:
                    add("warn", project_label, dt("project_unlinked"))
                    add("ok", dt("uv_project", name=env["name"]), dt("project_pending"))
            else:
                add("ok", dt("uv_shared", name=env["name"]), dt("shared_ok"))

            package_names = {canonicalize_name(str(p.get("name") or "")) for p in installed_packages(env["name"])}
            if "rf-mcp" in package_names:
                robotmcp = Path(m["venv"]) / ("Scripts/robotmcp.exe" if os.name == "nt" else "bin/robotmcp")
                add("ok" if robotmcp.exists() else "warn", f"RF-MCP {env['name']}", str(robotmcp) if robotmcp.exists() else dt("rfmcp_missing"))
            if "ollama" in package_names:
                ollama_runtime = find_ollama_executable()
                add("ok" if ollama_runtime else "warn", f"Ollama {env['name']}", str(ollama_runtime) if ollama_runtime else dt("ollama_missing"))
        except Exception as exc:
            add("error", env_name, str(exc))

    default_env = str(cfg.get("default_environment", "") or "")
    if default_env and default_env not in complete_names:
        add("warn", dt("default_env"), dt("default_missing", name=default_env))
    elif default_env:
        add("ok", dt("default_env"), default_env)

    try:
        port = int(cfg.get("web", {}).get("port", 0))
        host = str(cfg.get("web", {}).get("host", "127.0.0.1"))
        if port <= 0:
            auto_text={"fr":"port automatique (à partir de 8765)","en":"automatic port (starting at 8765)","de":"automatischer Port (ab 8765)","es":"puerto automático (desde 8765)","zh":"自动端口（从 8765 开始）"}.get(lang,"automatic port")
            add("ok", "Web", f"{host}:auto — {auto_text}")
        else:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                in_use = sock.connect_ex((host, port)) == 0
            add("warn" if in_use else "ok", "Web", f"{host}:{port} {dt('web_used') if in_use else dt('web_available')}")
    except Exception as exc:
        add("warn", "Web", str(exc))

    level_rank = {"ok": 0, "warn": 1, "error": 2}
    overall = max((level_rank[c["level"]] for c in checks), default=0)
    return {"version": APP_VERSION, "home": str(HOME), "status": ["ok", "warn", "error"][overall], "checks": checks, "language": lang}


def print_doctor(report: dict[str, Any]) -> None:
    lang = str(report.get("language") or _doctor_language())
    t = DOCTOR_I18N.get(lang, DOCTOR_I18N["en"])
    print(f"RFPY doctor v{report['version']}")
    print("=" * 60)
    labels = {"ok": "OK", "warn": "WARN", "error": "ERROR"}
    for c in report["checks"]:
        print(f"[{labels[c['level']]:5}] {c['name']:<22} {c['detail']}")
    print("=" * 60)
    print(f"{t['status']}: {report['status'].upper()}")

def pypi_metadata(package: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    with _metadata_lock:
        cached = _metadata_cache.get(package)
        if cached and time.time() - cached[0] < 900:
            return cached[1]
    data = http_get_json(f"https://pypi.org/pypi/{urllib.parse.quote(package)}/json", timeout=8, cfg=cfg)
    info = data.get("info", {})
    result = {
        "package": package,
        "version": info.get("version", ""),
        "requires_python": info.get("requires_python") or "",
        "summary": info.get("summary") or "",
    }
    with _metadata_lock:
        _metadata_cache[package] = (time.time(), result)
    return result


def python_probe_version(value: str) -> Version:
    value = (value or "").strip()
    if re.fullmatch(r"\d+\.\d+", value):
        value += ".0"
    try:
        return Version(value)
    except InvalidVersion:
        return Version("0")


def compatibility_catalog(python_version: str, env_name: str = "") -> dict[str, Any]:
    cfg = load_config()
    pyv = python_probe_version(python_version)
    installed: dict[str, str] = {}
    if env_name:
        with contextlib.suppress(Exception):
            installed = {p["name"].lower(): p["version"] for p in installed_packages(env_name)}
    standard = [
        {"name": name, "label": name, "version": str(pyv), "requires_python": "stdlib", "compatibility": "bundled", "detail": detail}
        for name, detail in STANDARD_LIBRARY_MODULES
    ]

    def one(item: tuple[str, str, str]) -> dict[str, Any]:
        package, label, category = item
        try:
            md = pypi_metadata(package, cfg)
            spec = str(md.get("requires_python", "") or "")
            if not spec:
                comp = "unknown"
            else:
                try:
                    comp = "compatible" if SpecifierSet(spec).contains(pyv, prereleases=True) else "incompatible"
                except Exception:
                    comp = "unknown"
            return {
                "name": package,
                "label": label,
                "category": category,
                "version": md.get("version", ""),
                "installed": installed.get(package.lower(), ""),
                "requires_python": spec or "non déclaré",
                "compatibility": comp,
                "summary": md.get("summary", ""),
            }
        except Exception as exc:
            return {"name": package, "label": label, "category": category, "version": "?", "installed": installed.get(package.lower(), ""), "requires_python": "?", "compatibility": "unknown", "summary": str(exc)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        third = list(pool.map(one, THIRD_PARTY_CATALOG))
    return {"python": str(pyv), "standard": standard, "third_party": third}


def robot_versions() -> list[str]:
    try:
        data = http_get_json("https://pypi.org/pypi/robotframework/json", timeout=8, cfg=load_config())
        versions=[]
        for raw in data.get("releases", {}):
            try: v=Version(raw)
            except InvalidVersion: continue
            if not v.is_prerelease and not v.is_devrelease: versions.append(raw)
        return sorted(versions,key=Version,reverse=True)
    except Exception:
        return []

def concise_robot_versions() -> list[dict[str,str]]:
    cfg=load_config(); vf=cfg.get("version_filters",{}); recent=bool(vf.get("robot_recent_only",True)); min_v=Version(str(vf.get("robot_min") or "6.0"))
    grouped={}
    for raw in robot_versions():
        try: v=Version(raw)
        except InvalidVersion: continue
        if recent and v < min_v: continue
        grouped.setdefault(f"{v.major}.{v.minor}",[]).append(v)
    def key(branch):
        a,b=branch.split(".",1); return int(a),int(b)
    return [{"branch":b,"version":str(sorted(grouped[b],reverse=True)[0])} for b in sorted(grouped,key=key,reverse=True)]


def concise_python_versions() -> list[dict[str, str]]:
    """One useful version per Python branch, optionally filtering legacy branches."""
    cfg=load_config(); vf=cfg.get("version_filters",{}); recent=bool(vf.get("python_recent_only",True)); min_v=Version(str(vf.get("python_min") or "3.10"))
    grouped: dict[str, list[Version]] = {}
    for raw in stable_versions_from_uv():
        try: v=Version(raw)
        except InvalidVersion: continue
        if recent and Version(f"{v.major}.{v.minor}") < min_v: continue
        grouped.setdefault(f"{v.major}.{v.minor}", []).append(v)
    def branch_key(branch: str) -> tuple[int, int]:
        major, minor = branch.split(".", 1); return int(major), int(minor)
    out=[]
    for branch in sorted(grouped,key=branch_key,reverse=True):
        vals=sorted(grouped[branch],reverse=True); finals=[v for v in vals if not v.is_prerelease and not v.is_devrelease]
        if finals: chosen=finals[0]; kind="stable"
        else:
            rcs=[v for v in vals if v.pre and v.pre[0]=="rc" and not v.is_devrelease]
            if not rcs: continue
            chosen=rcs[0]; kind="rc"
        out.append({"branch":branch,"version":str(chosen),"kind":kind})
    return out


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._processes: dict[str, subprocess.Popen[str]] = {}

    def create(self, action: str, fn: Callable[[Callable[[str], None]], Any]) -> str:
        job_id = uuid.uuid4().hex
        job = {"id": job_id, "action": action, "status": "running", "logs": [], "started_at": now_iso(), "ended_at": "", "result": None, "error": ""}
        with self._lock:
            self._jobs[job_id] = job
            self._cancel_events[job_id] = threading.Event()

        def log(line: str) -> None:
            with self._lock:
                job["logs"].append(str(line))
                job["logs"] = job["logs"][-500:]

        def worker() -> None:
            _job_context.job_id = job_id
            try:
                result = fn(log)
                with self._lock:
                    if self._cancel_events[job_id].is_set():
                        job["status"] = "cancelled"
                    else:
                        job["status"] = "done"
                        job["result"] = result
            except JobCancelled as exc:
                with self._lock:
                    job["status"] = "cancelled"
                    job["error"] = str(exc)
                    job["logs"].append(f"[ANNULÉ] {exc}")
            except Exception as exc:
                with self._lock:
                    job["status"] = "error"
                    job["error"] = str(exc)
                    job["logs"].append(f"[ERREUR] {exc}")
            finally:
                with self._lock:
                    job["ended_at"] = now_iso()
                    self._processes.pop(job_id, None)
                _job_context.job_id = ""

        threading.Thread(target=worker, name=f"rfpy-job-{job_id[:8]}", daemon=True).start()
        return job_id

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return json.loads(json.dumps(job)) if job else None

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            event = self._cancel_events.get(job_id)
            return bool(event and event.is_set())

    def register_process(self, job_id: str, proc: subprocess.Popen[str]) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._processes[job_id] = proc

    def clear_process(self, job_id: str, proc: subprocess.Popen[str]) -> None:
        with self._lock:
            if self._processes.get(job_id) is proc:
                self._processes.pop(job_id, None)

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise RfpyError("Job inconnu.")
            if job["status"] not in {"running", "cancelling"}:
                return json.loads(json.dumps(job))
            self._cancel_events[job_id].set()
            job["status"] = "cancelling"
            job["logs"].append("[INFO] Arrêt demandé…")
            proc = self._processes.get(job_id)
        if proc and proc.poll() is None:
            try:
                if os.name == "nt":
                    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    subprocess.run(
                        ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        creationflags=flags, check=False,
                    )
                else:
                    proc.terminate()
            except Exception:
                with contextlib.suppress(Exception):
                    proc.kill()
        return self.get(job_id) or {"id": job_id, "status": "cancelling"}


JOBS = JobStore()

WEB_HTML = r'''<!-- RFPY — Copyright © 2026 Olivier RENAULT — Apache-2.0 -->
<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RFPY</title>
<style>
:root{--bg:#0d1117;--panel:#161b22;--panel2:#0f1620;--line:#30363d;--text:#e6edf3;--muted:#8b949e;--accent:#58a6ff;--accent2:#16c7e8;--ok:#3fb950;--warn:#d29922;--bad:#f85149}
*{box-sizing:border-box} body{margin:0;font-family:Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text)} header{padding:12px 24px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:12px} .brand{display:flex;align-items:center;gap:12px} .brand img{width:58px;height:58px;object-fit:cover;border-radius:14px;border:1px solid var(--line)} .brand-title{display:flex;align-items:center;gap:10px} h1{margin:0;font-size:30px} h2,h3,h4{margin-top:0} .muted,.hint{color:var(--muted);font-size:12px} .actions,.row,.inline{display:flex;gap:8px;align-items:center;flex-wrap:wrap} .tabs{display:flex;gap:6px;padding:12px 20px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5} .tab,button{border:1px solid var(--line);background:#21262d;color:var(--text);padding:8px 12px;border-radius:8px;cursor:pointer} button:hover{border-color:#6e7681} .tab.active{color:var(--accent);border-color:var(--accent)} button.primary{background:#1f6feb} .danger{color:#ff7b72} main{max-width:1600px;margin:auto;padding:20px} .page{display:none} .page.active{display:block} .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:16px} .subcard{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:14px} .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px} .grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px} .stacked{display:grid;gap:10px} label{display:block;color:var(--muted);font-size:12px;margin-bottom:5px} input,select,textarea{width:100%;padding:8px;border:1px solid var(--line);border-radius:7px;background:var(--bg);color:var(--text)} input[readonly]{background:#111820} table{width:100%;border-collapse:collapse} th,td{padding:8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle} tr.sel{outline:1px solid var(--accent);background:#101b2b} .badge{display:inline-block;padding:2px 7px;border-radius:999px;border:1px solid var(--line);font-size:12px} .ok{color:var(--ok);border-color:var(--ok)} .bad{color:var(--bad);border-color:var(--bad)} .warn{color:var(--warn);border-color:var(--warn)} pre{white-space:pre-wrap;background:#010409;border:1px solid var(--line);padding:10px;max-height:360px;overflow:auto;border-radius:8px} .hidden{display:none!important} .pkggrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:9px} .pkg{border:1px solid var(--line);padding:10px;border-radius:9px;background:#111820} .error{color:var(--bad);min-height:24px} .repo-head,.repo{display:grid;grid-template-columns:1fr .7fr 1.7fr 1.5fr .45fr .55fr .45fr .55fr auto;gap:6px;align-items:center;margin-bottom:7px} .repo-head{font-size:11px;color:var(--muted);padding:0 4px} .lang-wrap{position:relative} .globe{font-size:38px;line-height:1;padding:2px 8px;background:transparent;border:none} .lang-menu{position:absolute;top:48px;left:0;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:6px;display:none;min-width:140px;z-index:20;box-shadow:0 10px 30px #0008} .lang-menu.open{display:grid} .lang-menu button{text-align:left;background:transparent;border:none} .radio-card{display:flex;gap:9px;align-items:flex-start;border:1px solid var(--line);padding:11px;border-radius:9px;background:#111820} .radio-card input{width:auto;margin-top:3px} .exports{display:grid;grid-template-columns:repeat(3,1fr);gap:12px} .export-card{border:1px solid var(--line);border-radius:10px;padding:14px;background:linear-gradient(145deg,#111820,#151d28)} .export-card strong{display:block;margin-bottom:6px} .compact{max-width:360px} .half{max-width:480px} .segmented{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden} .segmented label{margin:0;padding:8px 14px;color:var(--text);cursor:pointer} .segmented input{width:auto;margin-right:5px} .pathcell{max-width:390px;word-break:break-all} details{border:1px solid var(--line);padding:10px;border-radius:9px} summary{cursor:pointer;font-weight:600} .tooltip{cursor:help;border-bottom:1px dotted var(--muted)}.modal-overlay{position:fixed;inset:0;background:#000a;display:flex;align-items:center;justify-content:center;z-index:100}.modal{width:min(900px,92vw);max-height:84vh;background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:0 20px 70px #000;padding:18px;display:flex;flex-direction:column;gap:12px}.modal-title{display:flex;justify-content:space-between;align-items:center}.fs-favs{display:flex;gap:6px;flex-wrap:wrap}.fs-path{display:flex;gap:8px;align-items:center}.fs-path input{font-family:Consolas,monospace}.fs-list{border:1px solid var(--line);border-radius:10px;min-height:280px;max-height:48vh;overflow:auto;background:#0b1118}.fs-item{padding:9px 12px;border-bottom:1px solid #21262d;cursor:pointer;display:flex;gap:9px;align-items:center}.fs-item:hover,.fs-item.selected{background:#142238}.fs-icon{font-size:20px}.modal-footer{display:flex;justify-content:space-between;gap:10px;align-items:center}.modal-footer .right{display:flex;gap:8px}.file-native{display:none}

.settings-list{display:grid}.setting-row{display:grid;grid-template-columns:minmax(360px,1.2fr) minmax(280px,.8fr);gap:28px;padding:18px 0;border-top:1px solid var(--line);align-items:start}.setting-row:first-child{border-top:0}.setting-control h3{margin-bottom:10px}.setting-help{color:var(--muted);font-size:13px;line-height:1.5;padding-top:4px}.repo{display:block;margin:10px 0 0}.repo-fields{display:grid;grid-template-columns:minmax(150px,.9fr) minmax(120px,.55fr) minmax(220px,1.5fr) minmax(180px,1.1fr);gap:8px;align-items:end}.repo-options{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-top:10px}.repo-options label{margin:0}.repo-options input[type=checkbox]{width:auto}.repo-priority{width:100px!important}.settings-save{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.dirty-note{color:var(--warn);font-size:12px}.repo-empty{color:var(--muted);font-size:12px;margin-top:8px}
@media(max-width:900px){.setting-row{grid-template-columns:1fr}.repo-fields{grid-template-columns:1fr 1fr}.grid2,.exports{grid-template-columns:1fr} .repo-head{display:none} .repo{grid-template-columns:1fr 1fr} .tabs{overflow:auto} .brand img{display:none}}
</style></head><body>
<header><div class="brand"><img src="data:image/webp;base64,UklGRgATAABXRUJQVlA4IPQSAAAwTQCdASq0AJQAPj0ai0OiIaEWalUoIAPEtABnroCGb+S/Jz2aKy/Uvvd/X//V/gfir44dQ/4D0JvKP13/R/2n8r/hZ/ovZT+iv+x7gH6S/5n+u/4L9h/il9XPmD/o/94/af3i/8R+yvuq/v/+Z/xv9d+AX+q/4b/89gv+5XsCftB6uf/H/dL4O/2u/b/4E/53/hP/f7AH//9QDgde4b/FcuD7e6B38j+6/6b+6fuZyl/G3UC/GP5j/lPzC/JDmQwB/m39Q/4/G14gH6zcWjQD/SvoN/93+h9CX55/l//Z/lPgK/mv9k/6HS7+0if37m6HgSlJPXMKd5jmi7K5RuMYaTxz4QM0PoL7YBo4N7s67C4pv9kSaK397PO5trgbJ5OdoaGSUzbc/r8TmkkZBgBgPUjA5kZpanmuWxZWuHUpI9l0yBOA+V4IWHg93/u4ZfZBdprRi77lrolsVyjFxQ5MaBsjOLwSxQ6NoNm8cHnFmNVOwLvXYDoXiPb1xc1/Cah8URKUGtYHoGZPIF0u7HyZo3QbhEpPAFWLeldccYuRi7s2IrCierOHSP/kbv7B2SFiCkgt6ERilrva3TbLQjZuc6PlFzsPCscd/t55LHj0f/3IKAly+g32RVdK5vHgXf6VQoA5FolA74YpPsFTgG/ysNlHrQ0O6dqUj4+8lot/xHyOrJhQfb4L6oLKF2EXo6tPDf0WKvL6mrLyBjpl7iiw2KlsdJgEGlUjukHkKyn1WRTqu6fxaQc6F/J/FjSc3KdL98yNzFC7SInB/PZcPV0SkrQwD8bviRXneyfrSHYMIWLkVfCeSrxGS5jXHVvF4c1AAAD+/jrF2ufcN/0DqF3PVwWbLwX2xgEszycsSUXDcYDE6Ioez8xHPCyUxw1zWteiOM0KQDtDmX5YvsqKPAhSf2uaz0/ga2LkyxlqJsqou9W6kARhpgdfYw8Cb517XEqLj6nHDsd/F5LPImOIRG13ekAFny2UbVbnzePwzdLEMr45Qx6Y1/L/sUsr0WwlvsZi4cb82V+WuHkadq7bqPyaZOHiQHcyP4vx7tEO0bFWyU6FllTFwN7gE5qXiU730DM/XmbmNDUtSo3JU5vbSLdidKe9G3Yr2BKw6mPGZv+sW/AnwmSsm0VffR17QfLVoIA/8aDIA5W0rpW1nBnL3lwtn9Ypon8CU1lRiIunXGX1X/BzNvLWV7+0Hn9X5PqiAOcl9n1+BtifRa5l6H3FRzupbfBOMYkbwDBoSEZ+OGk8XwDUSxVJBzGJu9J307j5nn8xkQs3qjfkpktHHr0s2T6E4qXviKtty6yNBixCNk9vFEq7B+N4GfS/LkOaBg/wiStKsGBogj5OPfy17Z0hOjWJoAaYPq+5lUsHoxOgkTYBpeAnB0gZZhREr62i7m/BUiaA32FbyKvdpQzlgQ5GtOwZ17Sg5FOW1wh7ONNR4YnQCK6mn3u1hpwkQqburXok/ZrYidsMo7DkLIO2u00nTPf3qZejLdQBDSHq6NMyhOBIr5+DwNHb1RNAgDUg8U17tGfsQaLq5Xs1OezEkAYD7h9MaMT5+9t/Q6RvTQ8AmDYktF68sBg8B74XEAroiDejVr8Sa7shXE9wu3HuD4GG3ySf507uXL0CYigfWPYiyjfrkYQod1qB5aDA/A0KnjRMoB2XLY2h/yqB0DmavLK3PptZoWLLs851W5SAz7RGv2QZFPA0ioVom+8oLryFdL5kTaNStoBuYD7XYTDkPDPcoXnzudgn+19DPwhA8R029uyDvHCruCkl2PPLeXY8jCUulKp4D31HXbS5zdaH5Q3xHQHqNsyYFNn4GO8GGzf78hDsvkFLIefKsh5IdWb/dlmoDAMIGHLEyNwIJvIVUSJfYw16t2RCpK4zq3vxlLCqIt/zcHxxdeFultrSTNDYAJVFsjOVBCeyhof/SlXvvRDQzcavTkGOcVybP3x0XvLAEkgxPpVe4hQVsKdhx2i8XYcQiiqODxcLEml/T6si276WLMAJQmY+WizOoPMm2jmG+/nKCRhNcrp7tmMbrQ/btQiQzjz7C3047bYFHwkTCSiaf2MctlVK5Aol9KHZdw9xooq7f+5/0ybHLe5gwYbxcIRTYOMjbjsXlfSJz2Gp3Tcm7vemBnNaBmdxNEHKU9+sAVp/ipgc5DL97zH7NMDyzEqFErQOgY2B0CdPZoUahpHighDcr4qJ/yM/9oKAyjqYZCfyC9Y34W2uqOJLBnmYELZSdTEbZANjArsg1+vE6JTxTbUPmWzXnLMS5eJ3p0Gk1ukDHhl3p6gSTAjbt2EGHRUhyYbGmPIg19hKqZ+7tb4KIV95ajHSmeoRtmDEhUZ7dJd7IiH00B4etlzV3IFfxRYhmtnAd7WZQQR7vtdGHiqjNP1yfi6DXUJbvAV95vgtpuumsJ8b8qdYRjo2Ni3dZTwBZE8bUjB9/Hz/JA6uN3ous+/z2JaLZzQPWCTfbzLY5Ypi7LBS5eRMmqIEeagW3j/SG5L5c9iXqd4RREyPgMqUtcBJ3RngU63ickttHGjdMuV4q9LhqP2ZGSD6gURsXMXzxkMsze8so9STJF3Nqu5TX9nYvLCwyZzFMIyIeQIvux9QLz2ePeYQpRHN/z88z89vZWOrA+zZckg99I/9QjGgAe1n5inx5E7gl+fFL/OUEl6m3iEoNMCyj4Kfc8wvR5RgqR4QQ+qXBTqYWHOA2w8TymsNdECg9Ww6ThvyYeXLq1QSXS57ynoyE6aD/MOEXy2IrsRg1wxPbSvqpgMrajDPQvw44op9zMYbXEFceVBYu18Q7vHutNhFWXBZYMOXNEe4wJ92frVDGI4EY0YGmfDXlKq5fiUqctZKF/8dq5WtvM600X5b6v+/OwL/kR+oPZU+74NbO7ViNz2zKpLAiHVHhWSro26wr7EKLcEmBEIDeA6rJUB2MBXsih0//nBMtRsS4ern0tDd2tnJR5gnIaHZVoi6sNgyezWQLL/oh1+/7tfG92PBf6h64XYLz3/h8+VW7iBizUJtCWLE6ID4HlOvM14/0r05LcTM7OmWf5dDTnIi/1dMEJcGzYRM71EPFSObgdQGfGrqi3AB/TM34SqPHwlv+4JhyHNk583LsabeYWa/jg/IfxZApwZ093kxDutkrENJtq8YcQevnbVmOvflJ66EaYarP4O5ujCxSncug+JGHQpWeYc5oYQtqJjPE3ze5YbzEGOVopLClX4DHLDXkeDK1f5WyLjqJbVARR7WTHsvOZDbk/uKYlLhXqkE1znc/jwq82HT3D4wH61vt0WPt9TqFRpOA2rbuJF3VmaobQR3U7qTPrI0P3ZMhwDfwcFtNm9n4W4WQTap6NbCl5n4unJOR8ssh/sIWecQyG2toV9l6w1LP8CxGEg93HXSsw+ldJuHIF3WoMbwDcHppJQOC6twata2Rp7QNSKIr1eRJtsWsP8qg3mHV+kx/PQVR63o72+G2aWOHJn1P6xgIJNJwrqyS1NzUdiYLr/a2u6b9VphD+UgUikeKmZgAvSCLt1NR1F+udURU3MoMXvRwjKlzKcyI9YZEYd7JXQUm7ntu6xv6DrebRru/uHUxiEG/nPoUBNie0KJuUgPH3SdgPwI0OM7eG8TwXMTFjzjs/VbZajTwUA0fz6BFCOqwiopwFHpVVMngEnfO8UWZiuCyGAHZU3cETNKJKq8gFpX+DvZxKVgko86+diuEgVOkgZtZSDew1vZaRdEj31M1bYemE1ifDuJmBbk6u0S7kl86YYOQxe6+bESkbwld+Gb5eZgck7t7q+wee4pMqWvNpAjBs1wZkYtamwx4s144kKvPn33lFl4R0jsVDx2ukpqSaxBXZoI6HjhHKdECQ+eHiOmRUSqTQi7SjUNban/NAPKOwRFz02gRQFiANbzDNSWqcFe9oNFHaIuvJmWoMNAtWT5gJwAhBXv5SnAX+LPa2Ii7tUBB7vTYSG9TX/73if5FUs9rkLaO37gun9jbEHhQBixzh/Gq6jvBnd1RH9wonwZkEnoMeu3mShbUkoA2f3r+ma9vtf6D/TLbl154wwTk+auAbwpBTyj7wwWdWl9i9XLRDXPRR6kjuDzPEhkux9JOa+U3eD0J5fSlh+ZQ+X2VxdlB9ts1syPdf+w3DN6yiK9qIwf+Bp1YT/7Ft9rgOCFpHwzabkvfaLslhiulvnRxQuuWPCHiL6Y9uK3CcxOxJR7ti9SKygm2m4PcERmuyMkmHgWKQM0G3hyxqz7iKXnTKZONBWX+HzvA60/L03ZmF8K/2kkqRUsW9NgUNA+EzJxEPbftuJmxHWg4sq/ucv6JkHEsWb4FvkscVRAcVGv0hYb0dDefRh6euZaJKCELVq+HI18w4+FmR77iFvZPYop4pnDHufFcKRVa4+1WLSIstNOQeIY3uZv8x/HkGMTmGhlRuTdYYz5cUSQqcwA2tSZDUGRYRjumJzCezD/kdjVpvBJcUVLpYNxVlssHy1/RB/m1lTxvwSLjqCO6JGDRc9NW6oQlorOTyn2oXFzLVK7nKlJjG/5JyhnCkNo5DAa6O5jSSw27KzA7vOUZleJzIarpomJ1KJZBJDBH91XrymvtmggWeaVdZT+zzsVlZwkp7dtgydwiPe2FhQ2SQHADxzgtVkRDgFao83Q0Kp97rbul55jiWUfuxkRAjeEblJy2H/NH231ji35XCZIkvXwd2OxmyEDnMuD8JHfdF95VpZasduahRkgqnkqlVmbDhhUsvxtecfmPFcZp3wLp9loUdTGtu3divogCfvT+Dq7f1TMpmP9WwlzjJp3zMOTdhkNTDRtgtSo1DKMMyDLIGYpgoo6isWEDGi5nEo1KGdt/g0OneIIA9ihVGQBDvVPmTLayHfHuvcrNqqc8tDq2nu5g3HM4CBirXVSiwJJoI51usML/o+fr+blwYVUsR+2kSy9hsv0pqz1HozIMntyz+b2yXepu00R2wC6r1XigdEECkNv6/xC85oBrDuav7nkHsTNtnIhfu5AqfBPnC/L2IpHK27heynGuXPtPATVAzYf1nxTdJvpWN+KTP+HJzRR4o+4Abv5sRC2aNN8zidLbwdZutSHBX750hvwl7bK2VeFkRC1XAapEq2OJ6dCYIXT/08Q3jqqcL327oXIkzsYw84uttAkHxa6uFFI6OMZu45i5K/tikEx9fuCa/fnq3rrw1U3xTDadAwzAxNDJMEY7F7DLuvbmuLKdtAVFPlnGF+VQY7zj/VjCvXAWmqis7eqQxgxx6DlDVNIyvf5D7Oggu+zeQKbqisfXssXo5aJDyD60bXB7ymQEMCjvqf9MMGcgbLbqL1LjhVQO3O4cS1IO5F/9PFnJwf5QFaAP5f2sRkrF95qRZH6okxEo8amEFu1/X/9OXAEae5a4P01z91M7IGh/wT7DdWQHAad0P7qBJxD2vENJtZ4PQqzEBTOPrOy9NXjS1CoRzxjCkuCfe2BN9F5zAhwL8CqpF7iETXPuaFrIggTU24kLyV3/nm/iTIYA28UIFHJSLoMgIqb3Gr2zZYQ36o4TNitM+RNt8YPFbOeD5ISXUEHn+gEuTaykYcuKbE01DxiL/o0VhOmaHNto4sfdG0+NzcVwSZrGa3zvwm8mEc5bbt3Y7jixpxjz4jz9P4JN5rG8bku0R5c0n2NLjhP/EDJT09WwfU5PjcNAw46JrymtJpd+5jG1WtxdmRQ+U6oMcOkAUTA8ncNMwamuAQadfLoPtuc9/W1lTznOUxdia3PP0m/5ERjgyMMRe7etCQdHLjGWfu3nyXmD11ZJhyEgorrejsoPfpjKnExpA9zNyx8RZl8+J/apAkOvyoJW2OONLjiOTqWocqh+fNbre2j6bsJKxEcfGvposIRo+tthqk/r2pBBM/bzsI/3ObydktZDd+yOclzhnKnX015r701wLjIjVRJwNU4QPKyz6f2NwvVxWGD0XTN2TkGyM8dsiJEafuScVCL90lPuYzObeEKNxKSjhaRZ19SfaH6GJ4ufzfu3FZHJoRwARdDPcWkYNKaDsn+prbLoqOtskYu9FVRj8CwO+X2uA8kZPpkRLhSz8bxCzHanDw5/cqDlF3JyBggZZADMfAu7RdSuqpdun93wVHwYiA2t6R+oiRYe/uaZK/XQfQrlZK0+s8uaNjVsoyL3YMUCN4x14NWtCIIRASuwnuUIN+RYjYX4ObAZwkQzaq+5i6gXXq5nA2EyWwKR6aHokfir5CmNtPcCoCgXvpnJ7q9uKYncK+aMYHiXbthBFTSQMramT7W1UZowlWF6ko7g5JyWRyDxIeCbH+VKO6h0uHGADCIy2IN3IDLpcbe5yeWkoRkx9YIVYHv1uiLg0cfpo7CGsDSpdn/ZoqVT04WGr4KERXhmrMPpPG0TGu/DdOHCSqMznPFpQw00vbpa5i+0g/nPDHUpuJIOBlVNTnGPyWMUhVIpPhN9Yrg6P0ZHpYPVJVy44O6GtmvNT+Kigc4glOZCCABQpfsvpfPkAAA" alt="RFPY"><div><div class="brand-title"><h1>RFPY</h1><div class="lang-wrap"><button id="globe" class="globe" onclick="toggleLangMenu()" title="Language / Langue">🌐</button><div id="langMenu" class="lang-menu"><button onclick="setLang('fr')">🇫🇷 Français</button><button onclick="setLang('en')">🇬🇧 English</button><button onclick="setLang('de')">🇩🇪 Deutsch</button><button onclick="setLang('es')">🇪🇸 Español</button><button onclick="setLang('zh')">🇨🇳 中文</button></div></div></div><div class="muted" data-i="subtitle"></div></div></div><div class="actions"><span id="version" class="muted"></span><button class="danger" onclick="quitWeb()" data-i="quit"></button></div></header>
<div class="tabs"><button class="tab active" data-page="envs" data-i="envs"></button><button class="tab" data-page="install" data-i="installTab"></button><button class="tab" data-page="profiles" data-i="profilesTab"></button><button class="tab" data-page="settings" data-i="settings"></button><button class="tab" data-page="doctor" data-i="doctor"></button></div><main>
<section id="envs" class="page active"><div class="card"><div class="row"><h2 data-i="envs"></h2><button onclick="refreshAll()" data-i="refresh"></button></div><div id="envTable"></div><p class="muted" data-i="activateHint"></p></div><div class="card"><h2 data-i="content"></h2><div id="envSummary" class="muted"></div><div id="pipList"></div></div><div class="card"><h2 data-i="exports"></h2><p class="muted" data-i="exportsHint"></p><div class="exports"><div class="export-card"><strong>requirements.txt</strong><div class="muted" data-i="reqDesc"></div><div class="row" style="margin-top:10px"><button onclick="exportEnv('requirements')" data-i="generate"></button><button id="open-requirements" class="hidden" onclick="openExport('requirements')" data-i="open"></button></div><div id="path-requirements" class="hint"></div></div><div class="export-card"><strong>pyproject.toml</strong><div class="muted" data-i="pyprojectDesc"></div><div class="row" style="margin-top:10px"><button onclick="exportEnv('pyproject')" data-i="generate"></button><button id="open-pyproject" class="hidden" onclick="openExport('pyproject')" data-i="open"></button></div><div id="path-pyproject" class="hint"></div></div><div class="export-card"><strong>SBOM CycloneDX</strong><div class="muted" data-i="sbomDesc"></div><div class="row" style="margin-top:10px"><button onclick="exportEnv('sbom')" data-i="generate"></button><button id="open-sbom" class="hidden" onclick="openExport('sbom')" data-i="open"></button></div><div id="path-sbom" class="hint"></div></div></div></div></section>
<section id="install" class="page"><div class="card"><h2 data-i="newEnv"></h2><div class="stacked" style="margin-bottom:14px"><label class="radio-card"><input type="radio" name="envType" value="project" checked onchange="envTypeChanged()"><span><b data-i="project"></b><div class="hint" data-i="projectHint"></div></span></label><label class="radio-card"><input type="radio" name="envType" value="shared" onchange="envTypeChanged()"><span><b data-i="shared"></b><div class="hint" data-i="sharedHint"></div></span></label></div><div class="grid"><div><label data-i="name"></label><input id="iName"></div><div><label data-i="baseProfile"></label><select id="iProfile" onchange="baseProfileChanged()"><option value="playwright">Robot + Playwright</option><option value="selenium">Robot + Selenium</option><option value="robot">Robot Framework</option><option value="python">Python only</option></select></div><div><label data-i="installProfile"></label><select id="iInstallProfile"></select></div><div><label data-i="pythonVersion"></label><select id="iPython" onchange="pyChanged()"></select><div class="hint" data-i="branchHint"></div></div><div id="pyExactBox" class="hidden"><label data-i="customVersion"></label><input id="iPythonExact" placeholder="3.14.7"></div><div><label data-i="rfVersion"></label><select id="iRobot" onchange="rfChanged()"></select></div><div id="rfExactBox" class="hidden"><label data-i="customVersion"></label><input id="iRobotExact" placeholder="7.4.1"></div></div><div id="projectBox" class="subcard" style="margin-top:12px"><label data-i="projectFolder"></label><div class="row"><input id="iProject" readonly style="flex:1"><button onclick="pickInstallProject()" data-i="browse"></button><button onclick="clearInstallProject()" data-i="clear"></button></div><div id="projectProbe" class="hint" data-i="projectPending"></div><div id="existingBox" class="hidden" style="margin-top:10px"><label data-i="existing"></label><select id="iExisting" class="compact"><option value="use" data-i="useExisting"></option><option value="recreate" data-i="recreate"></option><option value="fail" data-i="fail"></option></select></div></div><div id="installError" class="error"></div><button class="primary" onclick="installEnv()" data-i="install"></button></div><div class="card"><div class="row"><h3 data-i="execution"></h3><button id="stopInstallJob" class="danger hidden" onclick="stopCurrentJob()" data-i="stop"></button></div><pre id="jobLog">—</pre></div><div class="card"><h3 data-i="quickTest"></h3><div class="grid"><div><label data-i="targetEnv"></label><select id="testEnv" onchange="testEnvChanged()"></select></div><div id="testWebOptions"><label data-i="testUrl"></label><input id="testUrl" value="https://www.google.com"><label style="margin-top:8px"><input id="testHeadless" type="checkbox" checked style="width:auto"> <span data-i="headless"></span></label></div></div><button onclick="runTest()" data-i="runTest"></button><pre id="testLog">—</pre></div></section>
<section id="profiles" class="page"><div class="card"><h2 data-i="targetEnv"></h2><p class="muted" data-i="targetHint"></p><div class="grid"><div class="half"><label data-i="name"></label><input id="pkgEnv" readonly></div><div class="compact"><label data-i="selectedPython"></label><input id="pkgPython" readonly></div></div></div><div class="card"><h2 data-i="librariesProfiles"></h2><div class="grid"><div><label data-i="profile"></label><select id="installationProfile"></select></div><div><label>&nbsp;</label><div class="segmented"><label><input type="radio" name="profileMode" value="merge" checked><span data-i="merge"></span></label><label><input type="radio" name="profileMode" value="replace"><span data-i="replace"></span></label></div></div></div><div class="hint" data-i="mergeHint"></div><div class="row" style="margin:10px 0"><button onclick="loadInstallProfile()" data-i="loadProfile"></button><button onclick="saveInstallProfile()" data-i="saveProfile"></button><button class="danger" onclick="deleteInstallProfile()" data-i="deleteProfile"></button></div><div class="grid"><div><label data-i="filter"></label><input id="pkgFilter" oninput="renderCatalog()"></div><div><label data-i="extra"></label><textarea id="extraPackages" rows="3" placeholder="robotframework-x==1.2&#10;requests>=2.32"></textarea></div></div><div class="row" style="margin-top:10px"><button class="primary" onclick="installPackages()" data-i="installSelection"></button><button onclick="$('profileImportFile').click()" data-i="importProfile"></button><input id="profileImportFile" class="file-native" type="file" accept=".txt,.toml" onchange="importProfileFile(this)"></div><details id="profileExecution" style="margin-top:14px"><summary data-i="profileExecution"></summary><div class="row" style="margin-top:10px"><button id="stopProfileJob" class="danger hidden" onclick="stopCurrentJob()" data-i="stop"></button></div><pre id="profileJobLog">—</pre></details></div><div class="card"><h2 data-i="rfLibraries"></h2><div id="pkgCatalog"></div><details style="margin-top:14px"><summary data-i="pythonSupport"></summary><div id="pySupportCatalog" style="margin-top:10px"></div></details></div></section>
<section id="settings" class="page">
<div class="card" id="repoCard">
  <div class="row" style="justify-content:space-between;align-items:flex-start">
    <div><h2 data-i="settings"></h2><div class="hint" data-i="settingsHint"></div></div>
    <div class="settings-save"><button id="settingsSaveTop" class="primary" onclick="saveSettings()" data-i="save"></button><span id="saved" class="muted"></span><span id="settingsDirty" class="dirty-note"></span></div>
  </div>
  <div class="settings-list">
    <div class="setting-row" id="publicPyPISection">
      <div class="setting-control"><h3 data-i="publicPyPI"></h3><label><input type="checkbox" id="aPublic" style="width:auto"> <span data-i="publicPyPI"></span></label><div id="pypiRepo"></div></div>
      <div class="setting-help" data-i="publicPyPIHelp"></div>
    </div>
    <div class="setting-row" id="privateRepositoriesSection">
      <div class="setting-control"><div class="row"><h3 data-i="privateRepos"></h3><button onclick="addRepoRow()">＋ <span data-i="addRepository"></span></button></div><label><input type="checkbox" id="aEnabled" style="width:auto" onchange="privateRepoToggleChanged()"> <span data-i="privateRepos"></span></label><div id="privateReposList"></div><div id="privateReposEmpty" class="repo-empty" data-i="privateReposEmpty"></div></div>
      <div class="setting-help" data-i="privateRepositoriesHelp"></div>
    </div>
    <div class="setting-row">
      <div class="setting-control"><h3 data-i="proxy"></h3><label><input type="checkbox" id="pEnabled" style="width:auto"> <span data-i="proxy"></span></label><label data-i="proxyUrl"></label><input id="pUrl" placeholder="http://proxy:8080"><label data-i="noProxy" style="margin-top:8px"></label><input id="pNo" placeholder="localhost,127.0.0.1"></div>
      <div class="setting-help" data-i="proxySectionHelp"></div>
    </div>
    <div class="setting-row">
      <div class="setting-control"><h3 data-i="customCA"></h3><div class="row"><input id="caBundle" readonly style="flex:1"><button onclick="pickCA()" data-i="browse"></button><button onclick="clearCA()" data-i="clear"></button></div><input id="caFileInput" class="file-native" type="file" accept=".pem,.crt,.cer" onchange="uploadCA(this)"></div>
      <div class="setting-help" data-i="caSectionHelp"></div>
    </div>
    <div class="setting-row">
      <div class="setting-control"><h3 data-i="webPort"></h3><label><input type="checkbox" id="webPortAuto" style="width:auto" onchange="webPortModeChanged()"> <span data-i="webPortAuto"></span></label><label data-i="webPortFixed"></label><input id="webPort" type="number" min="1" max="65535" class="compact"></div>
      <div class="setting-help" data-i="webPortSectionHelp"></div>
    </div>
    <div class="setting-row">
      <div class="setting-control"><h3 data-i="installSafety"></h3><div class="stacked"><label class="subcard"><input type="checkbox" id="binaryFallback" style="width:auto"> <b data-i="binaryFallback"></b><div class="hint" data-i="binaryFallbackHint"></div></label><label class="subcard"><input type="checkbox" id="cleanupCancelledNew" style="width:auto"> <b data-i="cleanupCancelledNew"></b><div class="hint" data-i="cleanupCancelledNewHint"></div></label></div></div>
      <div class="setting-help" data-i="installSafetyHelp"></div>
    </div>
    <div class="setting-row">
      <div class="setting-control"><h3 data-i="recentVersions"></h3><div class="stacked"><label class="subcard"><input type="checkbox" id="recentPython" style="width:auto"> <b data-i="recentPython"></b><div class="hint">Python ≥ <input id="pythonMin" value="3.10" style="width:80px;display:inline-block"></div></label><label class="subcard"><input type="checkbox" id="recentRobot" style="width:auto"> <b data-i="recentRobot"></b><div class="hint">Robot Framework ≥ <input id="robotMin" value="6.0" style="width:80px;display:inline-block"></div></label></div></div>
      <div class="setting-help" data-i="versionFiltersHelp"></div>
    </div>
    <div class="setting-row">
      <div class="setting-control"><h3 data-i="defaults"></h3><label data-i="baseProfile"></label><select id="dProfile" class="compact"><option>playwright</option><option>selenium</option><option>robot</option><option>python</option></select><label data-i="pythonVersion" style="margin-top:8px"></label><input id="dPython" class="compact" data-ph-i="emptyDefault" placeholder=""><label data-i="rfVersion" style="margin-top:8px"></label><input id="dRobot" class="compact" data-ph-i="emptyDefault" placeholder=""></div>
      <div class="setting-help" data-i="defaultsHelp"></div>
    </div>
  </div>
</div>
</section>
<section id="doctor" class="page"><div class="card"><div class="row"><h2 data-i="doctor"></h2><button onclick="loadDoctor()">↻</button></div><div id="doctorTable"></div></div></section>
</main>
<footer style="max-width:1600px;margin:0 auto 18px;padding:0 20px;color:var(--muted);font-size:12px">RFPY 1.0.0 — Copyright © 2026 Olivier RENAULT — Apache-2.0</footer>
<div id="folderModal" class="modal-overlay hidden">
  <div class="modal">
    <div class="modal-title"><h3 id="fsTitle" style="margin:0"></h3><button onclick="closeFolderBrowser()">×</button></div>
    <div id="fsFavs" class="fs-favs"></div>
    <div class="fs-path">
      <button id="fsUp" onclick="fsUp()">↑</button>
      <input id="fsCurrent" readonly>
      <button onclick="fsRefresh()">↻</button>
    </div>
    <div id="fsList" class="fs-list"></div>
    <div class="modal-footer">
      <button onclick="fsNewFolder()" data-i="newFolder"></button>
      <div class="right">
        <button onclick="closeFolderBrowser()" data-i="cancel"></button>
        <button class="primary" onclick="fsChooseCurrent()" data-i="chooseFolder"></button>
      </div>
    </div>
  </div>
</div>
<script>
// RFPY — Copyright © 2026 Olivier RENAULT — Apache-2.0
const L={"fr":{"subtitle":"Environnements Python + Robot Framework","quit":"Quitter","envs":"Environnements","installTab":"Installation","profilesTab":"Profils & bibliothèques","settings":"Paramétrage","refresh":"Actualiser","content":"Contenu du venv sélectionné","activateHint":"L’activation reste une action du shell : rfpy ou rfpy activate NOM.","newEnv":"Nouvel environnement","name":"Nom","baseProfile":"Socle technique","installProfile":"Profil de bibliothèques","project":"Projet — recommandé","projectHint":"Un environnement dédié à un seul projet. Le dossier projet peut être associé maintenant ou plus tard.","shared":"Partagé","sharedHint":"Environnement réutilisable. uv pip cible le venv actif ; les commandes projet sont protégées.","projectFolder":"Dossier du projet","browse":"Parcourir…","clear":"Effacer","projectPending":"Facultatif. Sans dossier, le venv Projet est préparé sous RFPY puis pourra être lié plus tard.","existing":"Si .venv existe déjà","useExisting":"Utiliser l’existant (recommandé)","recreate":"Le recréer","fail":"Arrêter","pythonVersion":"Version Python","rfVersion":"Version Robot Framework","customVersion":"Saisir une version…","noRf":"Ne pas installer","latest":"Dernière stable","install":"Installer","execution":"Exécution","quickTest":"Test rapide de l’installation","runTest":"Lancer le test","headless":"Headless","testUrl":"URL de test","targetEnv":"Environnement cible","targetHint":"Les bibliothèques seront installées dans l’environnement sélectionné dans l’onglet Environnements.","librariesProfiles":"Bibliothèques Robot Framework / profils d’installation","profile":"Profil","loadProfile":"Charger le profil","saveProfile":"Enregistrer la sélection comme profil","deleteProfile":"Supprimer le profil","merge":"Ajouter","replace":"Remplacer","mergeHint":"Ajouter complète la sélection actuelle. Remplacer repart uniquement du profil chargé.","filter":"Filtre","extra":"Bibliothèques supplémentaires","installSelection":"Installer la sélection","exports":"Fichiers de reproductibilité","exportsHint":"Générez les fichiers utiles pour reproduire, documenter ou auditer cet environnement. Après génération, vous pouvez les ouvrir directement.","generate":"Générer","open":"Ouvrir","projectPath":"Dossier du projet","link":"Associer","change":"Changer","duplicate":"Dupliquer","rename":"Renommer","delete":"Supprimer","setDefault":"Définir par défaut","privateRepos":"Dépôts privés / d’entreprise","privateReposHint":"Active l’utilisation des dépôts privés configurés ci-dessous. Laisser décoché si vous utilisez uniquement PyPI public.","addRepository":"Ajouter un dépôt","repositoriesHint":"Pour Nexus/Artifactory, renseignez au minimum l’URL Simple / PEP 503 utilisée par uv/pip.","privateRepoMissing":"Activez un dépôt privé uniquement après avoir ajouté au moins un dépôt Nexus, Artifactory ou Generic actif avec une URL Simple.","publicPyPI":"Autoriser PyPI public","proxy":"Utiliser un proxy","proxyUrl":"URL du proxy","noProxy":"NO_PROXY","customCA":"Certificat CA personnalisé","caHint":"Fichier PEM/CRT utilisé pour TLS par Python, requests, Node et les téléchargements. Laisser vide pour les certificats système.","repositories":"Dépôts / index Python","repoName":"Nom","repoType":"Type","simpleUrl":"URL Simple","browseUrl":"URL Browse/API","enabled":"Actif","installAll":"Installer tout","strict":"Strict","priority":"Priorité","recentVersions":"Versions proposées","recentPython":"Limiter Python aux branches récentes","recentRobot":"Limiter Robot Framework aux versions récentes","recentHint":"Décochez uniquement pour tester un contexte legacy. Les versions précises restent toujours saisissables.","defaults":"Valeurs par défaut","webPort":"Port Web","save":"Enregistrer","doctor":"Doctor","selectedPython":"Python du venv","language":"Langue","noProject":"Non lié","confirmChangeProject":"Changer le dossier projet déplace le .venv RFPY vers le nouveau projet. Continuer ?","duplicateName":"Nom du nouvel environnement","duplicateHint":"RFPY recrée le venv à partir du snapshot de packages en réutilisant le cache uv. Le dossier projet est remis à vide.","profileName":"Nom du profil","noneProfile":"Aucun profil","pythonSupport":"Dépendances Python de support","rfLibraries":"Bibliothèques Robot Framework","badName":"Nom invalide ou manquant.","needPython":"Choisissez une version Python.","needRf":"Choisissez une version Robot Framework pour ce socle.","saved":"Enregistré","status":"État","path":"Chemin","type":"Type","projectShort":"PROJET","sharedShort":"PARTAGÉ","reqDesc":"Snapshot des dépendances installées.","pyprojectDesc":"Base de projet moderne avec dépendances et version Python.","sbomDesc":"Python, npm, CPython, uv et relations de dépendances.","branchHint":"Une version par branche ; RC si aucune finale.","emptyDefault":"vide = aucun défaut","proxyTip":"Proxy HTTP/HTTPS utilisé par uv, les téléchargements Python et les index de packages.","privateRepoTip":"Index privés Nexus, Artifactory ou compatibles PyPI.","simpleTip":"URL d’index Simple / PEP 503 utilisée pour installer les packages.","browseTip":"URL Browse/API optionnelle utilisée pour découvrir les packages quand « Installer tout » est activé.","changeType":"Changer le type","confirmToProject":"Passer cet environnement en Projet ? Le venv reste en place tant qu’aucun dossier projet n’est associé.","confirmToShared":"Passer cet environnement en Partagé ? Si un dossier projet est lié, le .venv géré par RFPY sera déplacé sous RFPY et le lien projet sera supprimé.","chooseFolder":"Choisir ce dossier","newFolder":"Nouveau dossier","cancel":"Annuler","folderBrowser":"Choisir un dossier","folderName":"Nom du nouveau dossier","caUploaded":"Certificat copié dans RFPY","stop":"Arrêter","stopping":"Arrêt en cours…","profileExecution":"Exécution du profil","importProfile":"Importer requirements.txt / pyproject.toml","importProfileDone":"Profil importé","binaryFallback":"Fallback wheel binaire sur erreur Visual C++ / MSVC","binaryFallbackHint":"Après une erreur de compilation MSVC, RFPY tente uniquement pour le package fautif un wheel binaire compatible. Le mode binaire n’est pas imposé par défaut.","cleanupCancelledNew":"Nettoyer un nouvel environnement annulé","cleanupCancelledNewHint":"Si RFPY vient de créer le .venv, une annulation supprime l’environnement incomplet. Un .venv préexistant n’est jamais supprimé.","installSafety":"Installation / annulation","importWarnings":"Avertissements","jobRunning":"Un traitement RFPY est déjà en cours.","venvLabel":"Venv","pipList":"Liste des packages","package":"Package","versionLabel":"Version","stopped":"RFPY arrêté.","configureRepositories":"Configurer les dépôts","webPortAuto":"Port automatique","webPortFixed":"Port personnalisé","webPortHint":"En mode automatique, RFPY choisit le premier port disponible à partir de 8765.","invalidWebPort":"Le port Web doit être compris entre 1 et 65535.","repoEnableHint":"Activez les dépôts privés puis configurez au moins une URL Simple Nexus/Artifactory.","latestLabel":"dernière","installedLabel":"installé","errorLabel":"Erreur","statusDefault":"défaut","statusOk":"OK","statusCompatible":"compatible","statusBundled":"inclus","statusError":"erreur","statusIncompatible":"incompatible","categoryPythonSupport":"Support Python","categoryWeb":"Web","categoryAPI":"API","categoryData":"Données","categoryDatabase":"Base de données","categorySystem":"Système","categoryDocuments":"Documents","categoryMobile":"Mobile","categoryDesktop":"Bureau","categoryRPA":"RPA / Bureau","categoryFilesArchive":"Fichiers / Archives","categoryMessaging":"Messagerie","categoryAILLM":"IA / LLM","settingsHint":"Tous les paramètres de cette page sont enregistrés ensemble. Enregistrez-les avant de quitter.","publicPyPIHelp":"Active ou désactive l’index public PyPI. L’URL Simple / PEP 503 ci-contre est celle transmise à uv/pip.","privateRepositoriesHelp":"Les dépôts internes sont optionnels. Plusieurs dépôts peuvent être actifs simultanément ; la priorité détermine leur ordre. Tout dépôt actif doit avoir une URL Simple / PEP 503.","privateReposEmpty":"Aucun dépôt privé configuré.","proxySectionHelp":"Proxy HTTP/HTTPS utilisé par uv, Python et les téléchargements. NO_PROXY permet d’exclure les hôtes locaux ou internes.","caSectionHelp":"Certificat PEM/CRT supplémentaire pour les dépôts ou proxys TLS d’entreprise. Laisser vide pour utiliser les certificats système.","webPortSectionHelp":"Le mode automatique évite les collisions entre consoles locales en choisissant le premier port libre à partir de 8765.","installSafetyHelp":"Contrôle le fallback binaire MSVC et le nettoyage des nouveaux environnements annulés.","versionFiltersHelp":"Limite les versions proposées dans l’interface sans empêcher la saisie d’une version précise.","defaultsHelp":"Valeurs préremplies lors de la création d’un nouvel environnement.","unsavedSettingsQuit":"Des paramètres ont été modifiés sans être enregistrés. Quitter et perdre ces modifications ?","unsavedChanges":"Modifications non enregistrées","enabledRepoNeedsUrl":"Un dépôt actif doit avoir une URL Simple / PEP 503 : ","invalidRepoUrl":"URL de dépôt invalide (http:// ou https:// attendu) : "},"en":{"subtitle":"Python + Robot Framework environments","quit":"Quit","envs":"Environments","installTab":"Installation","profilesTab":"Profiles & libraries","settings":"Settings","refresh":"Refresh","content":"Selected virtual environment","activateHint":"Activation changes the current shell: rfpy or rfpy activate NAME.","newEnv":"New environment","name":"Name","baseProfile":"Technical base","installProfile":"Library profile","project":"Project — recommended","projectHint":"Dedicated to one project. The project folder can be linked now or later.","shared":"Shared","sharedHint":"Reusable environment. uv pip targets the active venv; project commands are protected.","projectFolder":"Project folder","browse":"Browse…","clear":"Clear","projectPending":"Optional. Without a folder, the Project venv is prepared under RFPY and can be linked later.","existing":"If .venv already exists","useExisting":"Use existing (recommended)","recreate":"Recreate","fail":"Stop","pythonVersion":"Python version","rfVersion":"Robot Framework version","customVersion":"Enter a version…","noRf":"Do not install","latest":"Latest stable","install":"Install","execution":"Execution","quickTest":"Quick installation test","runTest":"Run test","headless":"Headless","testUrl":"Test URL","targetEnv":"Target environment","targetHint":"Libraries are installed into the environment selected in the Environments tab.","librariesProfiles":"Robot Framework libraries / installation profiles","profile":"Profile","loadProfile":"Load profile","saveProfile":"Save selection as profile","deleteProfile":"Delete profile","merge":"Add","replace":"Replace","mergeHint":"Add merges with the current selection. Replace resets to the loaded profile.","filter":"Filter","extra":"Additional libraries","installSelection":"Install selection","exports":"Reproducibility files","exportsHint":"Generate files to reproduce, document or audit this environment. You can open them directly after generation.","generate":"Generate","open":"Open","projectPath":"Project folder","link":"Link","change":"Change","duplicate":"Duplicate","rename":"Rename","delete":"Delete","setDefault":"Set default","privateRepos":"Private / enterprise repositories","privateReposHint":"Enables the private repositories configured below. Leave unchecked when using public PyPI only.","addRepository":"Add repository","repositoriesHint":"For Nexus/Artifactory, provide at least the Simple / PEP 503 URL used by uv/pip.","privateRepoMissing":"Enable private repositories only after adding at least one enabled Nexus, Artifactory or Generic repository with a Simple URL.","publicPyPI":"Allow public PyPI","proxy":"Use proxy","proxyUrl":"Proxy URL","noProxy":"NO_PROXY","customCA":"Custom CA certificate","caHint":"PEM/CRT file used for TLS by Python, requests, Node and downloads. Leave empty for system certificates.","repositories":"Repositories / Python indexes","repoName":"Name","repoType":"Type","simpleUrl":"Simple URL","browseUrl":"Browse/API URL","enabled":"Enabled","installAll":"Install all","strict":"Strict","priority":"Priority","recentVersions":"Suggested versions","recentPython":"Limit Python to recent branches","recentRobot":"Limit Robot Framework to recent versions","recentHint":"Uncheck only for legacy testing. Exact versions can always be entered.","defaults":"Defaults","webPort":"Web port","save":"Save","doctor":"Doctor","selectedPython":"Environment Python","language":"Language","noProject":"Not linked","confirmChangeProject":"Changing the project folder moves the RFPY .venv to the new project. Continue?","duplicateName":"New environment name","duplicateHint":"RFPY recreates the venv from the package snapshot and reuses the uv cache. The project folder is reset.","profileName":"Profile name","noneProfile":"No profile","pythonSupport":"Python support dependencies","rfLibraries":"Robot Framework libraries","badName":"Missing or invalid name.","needPython":"Choose a Python version.","needRf":"Choose a Robot Framework version for this base.","saved":"Saved","status":"Status","path":"Path","type":"Type","projectShort":"PROJECT","sharedShort":"SHARED","reqDesc":"Snapshot of installed dependencies.","pyprojectDesc":"Modern project base with dependencies and Python version.","sbomDesc":"Python, npm, CPython, uv and dependency relationships.","branchHint":"One version per branch; RC only when no final release exists.","emptyDefault":"empty = no default","proxyTip":"HTTP/HTTPS proxy used by uv, Python downloads and package indexes.","privateRepoTip":"Private Nexus, Artifactory or PyPI-compatible indexes.","simpleTip":"Simple / PEP 503 index URL used to install packages.","browseTip":"Optional Browse/API URL used to discover packages when “Install all” is enabled.","changeType":"Change type","confirmToProject":"Switch this environment to Project? The venv stays where it is until a project folder is linked.","confirmToShared":"Switch this environment to Shared? If a project folder is linked, the RFPY-managed .venv is moved back under RFPY and the project link is cleared.","chooseFolder":"Choose this folder","newFolder":"New folder","cancel":"Cancel","folderBrowser":"Choose a folder","folderName":"New folder name","caUploaded":"Certificate copied into RFPY","stop":"Stop","stopping":"Stopping…","profileExecution":"Profile execution","importProfile":"Import requirements.txt / pyproject.toml","importProfileDone":"Profile imported","binaryFallback":"Binary-wheel fallback on Visual C++ / MSVC error","binaryFallbackHint":"After an MSVC build error, RFPY retries only the failing package with a compatible binary wheel. Binary-only mode is not forced by default.","cleanupCancelledNew":"Clean up a cancelled new environment","cleanupCancelledNewHint":"If RFPY has just created the venv, cancelling removes the incomplete environment. A pre-existing venv is never deleted.","installSafety":"Installation / cancellation","importWarnings":"Warnings","jobRunning":"An RFPY operation is already running.","venvLabel":"Venv","pipList":"Package list","package":"Package","versionLabel":"Version","stopped":"RFPY stopped.","configureRepositories":"Configure repositories","webPortAuto":"Automatic port","webPortFixed":"Custom port","webPortHint":"In automatic mode, RFPY selects the first available port starting at 8765.","invalidWebPort":"The Web port must be between 1 and 65535.","repoEnableHint":"Enable private repositories, then configure at least one Nexus/Artifactory Simple URL.","latestLabel":"latest","installedLabel":"installed","errorLabel":"Error","statusDefault":"default","statusOk":"OK","statusCompatible":"compatible","statusBundled":"bundled","statusError":"error","statusIncompatible":"incompatible","categoryPythonSupport":"Python support","categoryWeb":"Web","categoryAPI":"API","categoryData":"Data","categoryDatabase":"Database","categorySystem":"System","categoryDocuments":"Documents","categoryMobile":"Mobile","categoryDesktop":"Desktop","categoryRPA":"RPA / Desktop","categoryFilesArchive":"Files / Archive","categoryMessaging":"Messaging","categoryAILLM":"AI / LLM","settingsHint":"All settings on this page are saved together. Save them before quitting.","publicPyPIHelp":"Enables or disables the public PyPI index. The Simple / PEP 503 URL shown here is passed to uv/pip.","privateRepositoriesHelp":"Internal repositories are optional. Multiple repositories may be enabled at the same time; priority determines their order. Every enabled repository must have a Simple / PEP 503 URL.","privateReposEmpty":"No private repository configured.","proxySectionHelp":"HTTP/HTTPS proxy used by uv, Python and downloads. NO_PROXY excludes local or internal hosts.","caSectionHelp":"Additional PEM/CRT certificate for enterprise TLS repositories or proxies. Leave empty to use system certificates.","webPortSectionHelp":"Automatic mode avoids collisions between local consoles by selecting the first free port starting at 8765.","installSafetyHelp":"Controls the MSVC binary-wheel fallback and cleanup of cancelled new environments.","versionFiltersHelp":"Limits versions suggested by the UI without preventing an exact version from being entered.","defaultsHelp":"Values pre-filled when creating a new environment.","unsavedSettingsQuit":"Settings have unsaved changes. Quit and lose these changes?","unsavedChanges":"Unsaved changes","enabledRepoNeedsUrl":"An enabled repository must have a Simple / PEP 503 URL: ","invalidRepoUrl":"Invalid repository URL (expected http:// or https://): "},"de":{"subtitle":"Python- + Robot-Framework-Umgebungen","quit":"Beenden","envs":"Umgebungen","installTab":"Installation","profilesTab":"Profile & Bibliotheken","settings":"Einstellungen","refresh":"Aktualisieren","content":"Ausgewählte virtuelle Umgebung","activateHint":"Aktivierung erfolgt in der Shell: rfpy oder rfpy activate NAME.","newEnv":"Neue Umgebung","name":"Name","baseProfile":"Technische Basis","installProfile":"Bibliotheksprofil","project":"Projekt — empfohlen","projectHint":"Für ein einziges Projekt. Der Projektordner kann jetzt oder später verknüpft werden.","shared":"Geteilt","sharedHint":"Wiederverwendbare Umgebung. uv pip verwendet das aktive venv; Projektbefehle sind geschützt.","projectFolder":"Projektordner","browse":"Durchsuchen…","clear":"Leeren","projectPending":"Optional. Ohne Ordner wird das Projekt-venv unter RFPY vorbereitet und kann später verknüpft werden.","existing":"Wenn .venv bereits existiert","useExisting":"Vorhandenes verwenden","recreate":"Neu erstellen","fail":"Stoppen","pythonVersion":"Python-Version","rfVersion":"Robot-Framework-Version","customVersion":"Version eingeben…","noRf":"Nicht installieren","latest":"Neueste stabile","install":"Installieren","execution":"Ausführung","quickTest":"Schnelltest","runTest":"Test starten","headless":"Headless","testUrl":"Test-URL","targetEnv":"Zielumgebung","targetHint":"Bibliotheken werden in die im Tab Umgebungen ausgewählte Umgebung installiert.","librariesProfiles":"Robot-Framework-Bibliotheken / Installationsprofile","profile":"Profil","loadProfile":"Profil laden","saveProfile":"Auswahl als Profil speichern","deleteProfile":"Profil löschen","merge":"Hinzufügen","replace":"Ersetzen","mergeHint":"Hinzufügen ergänzt die aktuelle Auswahl. Ersetzen setzt auf das Profil zurück.","filter":"Filter","extra":"Zusätzliche Bibliotheken","installSelection":"Auswahl installieren","exports":"Reproduzierbarkeitsdateien","exportsHint":"Dateien zur Reproduktion, Dokumentation oder Prüfung erzeugen und anschließend direkt öffnen.","generate":"Erzeugen","open":"Öffnen","projectPath":"Projektordner","link":"Verknüpfen","change":"Ändern","duplicate":"Duplizieren","rename":"Umbenennen","delete":"Löschen","setDefault":"Als Standard","privateRepos":"Private / Unternehmens-Repositories","privateReposHint":"Aktiviert die unten konfigurierten privaten Repositories. Deaktiviert lassen, wenn nur öffentliches PyPI verwendet wird.","addRepository":"Repository hinzufügen","repositoriesHint":"Für Nexus/Artifactory mindestens die Simple-/PEP-503-URL für uv/pip angeben.","privateRepoMissing":"Private Repositories erst aktivieren, nachdem mindestens ein aktives Nexus-, Artifactory- oder Generic-Repository mit Simple-URL hinzugefügt wurde.","publicPyPI":"Öffentliches PyPI erlauben","proxy":"Proxy verwenden","proxyUrl":"Proxy-URL","noProxy":"NO_PROXY","customCA":"Benutzerdefiniertes CA-Zertifikat","caHint":"PEM/CRT-Datei für TLS. Leer lassen für Systemzertifikate.","repositories":"Repositories / Python-Indizes","repoName":"Name","repoType":"Typ","simpleUrl":"Simple-URL","browseUrl":"Browse/API-URL","enabled":"Aktiv","installAll":"Alles installieren","strict":"Strikt","priority":"Priorität","recentVersions":"Vorgeschlagene Versionen","recentPython":"Python auf neue Zweige begrenzen","recentRobot":"Robot Framework auf neue Versionen begrenzen","recentHint":"Nur für Legacy-Tests deaktivieren. Exakte Versionen bleiben möglich.","defaults":"Standardwerte","webPort":"Web-Port","save":"Speichern","doctor":"Doctor","selectedPython":"Python der Umgebung","language":"Sprache","noProject":"Nicht verknüpft","confirmChangeProject":"Beim Ändern wird das RFPY-.venv in das neue Projekt verschoben. Fortfahren?","duplicateName":"Name der neuen Umgebung","duplicateHint":"RFPY erstellt das venv aus dem Paket-Snapshot neu und nutzt den uv-Cache. Der Projektordner wird geleert.","profileName":"Profilname","noneProfile":"Kein Profil","pythonSupport":"Python-Hilfsabhängigkeiten","rfLibraries":"Robot-Framework-Bibliotheken","badName":"Name fehlt oder ist ungültig.","needPython":"Python-Version wählen.","needRf":"Robot-Framework-Version wählen.","saved":"Gespeichert","status":"Status","path":"Pfad","type":"Typ","projectShort":"PROJEKT","sharedShort":"GETEILT","reqDesc":"Momentaufnahme der installierten Abhängigkeiten.","pyprojectDesc":"Moderne Projektbasis mit Abhängigkeiten und Python-Version.","sbomDesc":"Python, npm, CPython, uv und Abhängigkeitsbeziehungen.","branchHint":"Eine Version pro Zweig; RC nur wenn keine finale Version existiert.","emptyDefault":"leer = kein Standardwert","proxyTip":"HTTP/HTTPS-Proxy für uv, Python-Downloads und Paketindizes.","privateRepoTip":"Private Nexus-, Artifactory- oder PyPI-kompatible Indizes.","simpleTip":"Simple-/PEP-503-Index-URL zur Paketinstallation.","browseTip":"Optionale Browse/API-URL zur Paketentdeckung bei aktiviertem „Alle installieren“.","changeType":"Typ ändern","confirmToProject":"Diese Umgebung in Projekt umwandeln? Das venv bleibt zunächst an seinem Ort, bis ein Projektordner verknüpft wird.","confirmToShared":"Diese Umgebung in Geteilt umwandeln? Bei verknüpftem Projekt wird das von RFPY verwaltete .venv zurück unter RFPY verschoben und die Projektverknüpfung entfernt.","chooseFolder":"Diesen Ordner wählen","newFolder":"Neuer Ordner","cancel":"Abbrechen","folderBrowser":"Ordner wählen","folderName":"Name des neuen Ordners","caUploaded":"Zertifikat nach RFPY kopiert","stop":"Stoppen","stopping":"Wird gestoppt…","profileExecution":"Profilausführung","importProfile":"requirements.txt / pyproject.toml importieren","importProfileDone":"Profil importiert","binaryFallback":"Binäres Wheel bei Visual-C++-/MSVC-Fehler","binaryFallbackHint":"Nach einem MSVC-Buildfehler versucht RFPY nur für das fehlgeschlagene Paket ein kompatibles binäres Wheel. Binär-only ist nicht Standard.","cleanupCancelledNew":"Abgebrochene neue Umgebung bereinigen","cleanupCancelledNewHint":"Wenn RFPY das venv gerade erstellt hat, wird eine unvollständige Umgebung beim Abbruch entfernt. Ein vorhandenes venv wird nie gelöscht.","installSafety":"Installation / Abbruch","importWarnings":"Warnungen","jobRunning":"Ein RFPY-Vorgang läuft bereits.","venvLabel":"Venv","pipList":"Paketliste","package":"Paket","versionLabel":"Version","stopped":"RFPY beendet.","configureRepositories":"Repositories konfigurieren","webPortAuto":"Automatischer Port","webPortFixed":"Benutzerdefinierter Port","webPortHint":"Im automatischen Modus wählt RFPY den ersten freien Port ab 8765.","invalidWebPort":"Der Web-Port muss zwischen 1 und 65535 liegen.","repoEnableHint":"Private Repositories aktivieren und anschließend mindestens eine Nexus/Artifactory-Simple-URL konfigurieren.","latestLabel":"neueste","installedLabel":"installiert","errorLabel":"Fehler","statusDefault":"Standard","statusOk":"OK","statusCompatible":"kompatibel","statusBundled":"enthalten","statusError":"Fehler","statusIncompatible":"inkompatibel","categoryPythonSupport":"Python-Unterstützung","categoryWeb":"Web","categoryAPI":"API","categoryData":"Daten","categoryDatabase":"Datenbank","categorySystem":"System","categoryDocuments":"Dokumente","categoryMobile":"Mobil","categoryDesktop":"Desktop","categoryRPA":"RPA / Desktop","categoryFilesArchive":"Dateien / Archive","categoryMessaging":"Nachrichten","categoryAILLM":"KI / LLM","settingsHint":"Alle Einstellungen auf dieser Seite werden gemeinsam gespeichert. Speichern Sie sie vor dem Beenden.","publicPyPIHelp":"Aktiviert oder deaktiviert den öffentlichen PyPI-Index. Die angezeigte Simple-/PEP-503-URL wird an uv/pip übergeben.","privateRepositoriesHelp":"Interne Repositories sind optional. Mehrere Repositories können gleichzeitig aktiv sein; die Priorität bestimmt ihre Reihenfolge. Jedes aktive Repository benötigt eine Simple-/PEP-503-URL.","privateReposEmpty":"Kein privates Repository konfiguriert.","proxySectionHelp":"HTTP/HTTPS-Proxy für uv, Python und Downloads. NO_PROXY schließt lokale oder interne Hosts aus.","caSectionHelp":"Zusätzliches PEM/CRT-Zertifikat für Unternehmens-Repositories oder TLS-Proxys. Leer lassen, um Systemzertifikate zu verwenden.","webPortSectionHelp":"Der automatische Modus vermeidet Kollisionen lokaler Konsolen und wählt ab Port 8765 den ersten freien Port.","installSafetyHelp":"Steuert den MSVC-Binary-Wheel-Fallback und die Bereinigung abgebrochener neuer Umgebungen.","versionFiltersHelp":"Begrenzt die vorgeschlagenen Versionen, ohne die Eingabe einer exakten Version zu verhindern.","defaultsHelp":"Vorbelegte Werte beim Erstellen einer neuen Umgebung.","unsavedSettingsQuit":"Es gibt nicht gespeicherte Einstellungen. Beenden und diese Änderungen verwerfen?","unsavedChanges":"Nicht gespeicherte Änderungen","enabledRepoNeedsUrl":"Ein aktives Repository benötigt eine Simple-/PEP-503-URL: ","invalidRepoUrl":"Ungültige Repository-URL (http:// oder https:// erwartet): "},"es":{"subtitle":"Entornos Python + Robot Framework","quit":"Salir","envs":"Entornos","installTab":"Instalación","profilesTab":"Perfiles y bibliotecas","settings":"Configuración","refresh":"Actualizar","content":"Entorno virtual seleccionado","activateHint":"La activación modifica la shell: rfpy o rfpy activate NOMBRE.","newEnv":"Nuevo entorno","name":"Nombre","baseProfile":"Base técnica","installProfile":"Perfil de bibliotecas","project":"Proyecto — recomendado","projectHint":"Dedicado a un solo proyecto. La carpeta puede vincularse ahora o después.","shared":"Compartido","sharedHint":"Entorno reutilizable. uv pip usa el venv activo; los comandos de proyecto están protegidos.","projectFolder":"Carpeta del proyecto","browse":"Examinar…","clear":"Limpiar","projectPending":"Opcional. Sin carpeta, el venv de Proyecto se prepara en RFPY y puede vincularse más tarde.","existing":"Si .venv ya existe","useExisting":"Usar el existente","recreate":"Recrear","fail":"Detener","pythonVersion":"Versión de Python","rfVersion":"Versión de Robot Framework","customVersion":"Introducir una versión…","noRf":"No instalar","latest":"Última estable","install":"Instalar","execution":"Ejecución","quickTest":"Prueba rápida","runTest":"Ejecutar prueba","headless":"Headless","testUrl":"URL de prueba","targetEnv":"Entorno objetivo","targetHint":"Las bibliotecas se instalan en el entorno seleccionado en Entornos.","librariesProfiles":"Bibliotecas Robot Framework / perfiles de instalación","profile":"Perfil","loadProfile":"Cargar perfil","saveProfile":"Guardar selección como perfil","deleteProfile":"Eliminar perfil","merge":"Añadir","replace":"Reemplazar","mergeHint":"Añadir completa la selección actual. Reemplazar reinicia al perfil cargado.","filter":"Filtro","extra":"Bibliotecas adicionales","installSelection":"Instalar selección","exports":"Archivos de reproducibilidad","exportsHint":"Genera archivos para reproducir, documentar o auditar el entorno y ábrelos directamente.","generate":"Generar","open":"Abrir","projectPath":"Carpeta del proyecto","link":"Vincular","change":"Cambiar","duplicate":"Duplicar","rename":"Renombrar","delete":"Eliminar","setDefault":"Predeterminado","privateRepos":"Repositorios privados / empresa","privateReposHint":"Activa los repositorios privados configurados abajo. Déjelo desmarcado si solo usa PyPI público.","addRepository":"Añadir repositorio","repositoriesHint":"Para Nexus/Artifactory, indique al menos la URL Simple / PEP 503 usada por uv/pip.","privateRepoMissing":"Active los repositorios privados solo después de añadir al menos un repositorio Nexus, Artifactory o Generic activo con una URL Simple.","publicPyPI":"Permitir PyPI público","proxy":"Usar proxy","proxyUrl":"URL del proxy","noProxy":"NO_PROXY","customCA":"Certificado CA personalizado","caHint":"Archivo PEM/CRT usado para TLS. Vacío = certificados del sistema.","repositories":"Repositorios / índices Python","repoName":"Nombre","repoType":"Tipo","simpleUrl":"URL Simple","browseUrl":"URL Browse/API","enabled":"Activo","installAll":"Instalar todo","strict":"Estricto","priority":"Prioridad","recentVersions":"Versiones sugeridas","recentPython":"Limitar Python a ramas recientes","recentRobot":"Limitar Robot Framework a versiones recientes","recentHint":"Desmarcar solo para contextos legacy. Las versiones exactas siempre se pueden escribir.","defaults":"Valores predeterminados","webPort":"Puerto Web","save":"Guardar","doctor":"Doctor","selectedPython":"Python del entorno","language":"Idioma","noProject":"No vinculado","confirmChangeProject":"Cambiar la carpeta mueve el .venv RFPY al nuevo proyecto. ¿Continuar?","duplicateName":"Nombre del nuevo entorno","duplicateHint":"RFPY recrea el venv desde el snapshot de paquetes usando la caché uv. La carpeta de proyecto queda vacía.","profileName":"Nombre del perfil","noneProfile":"Sin perfil","pythonSupport":"Dependencias Python de soporte","rfLibraries":"Bibliotecas Robot Framework","badName":"Nombre inválido o ausente.","needPython":"Selecciona una versión Python.","needRf":"Selecciona una versión Robot Framework.","saved":"Guardado","status":"Estado","path":"Ruta","type":"Tipo","projectShort":"PROYECTO","sharedShort":"COMPARTIDO","reqDesc":"Instantánea de las dependencias instaladas.","pyprojectDesc":"Base de proyecto moderna con dependencias y versión de Python.","sbomDesc":"Python, npm, CPython, uv y relaciones de dependencias.","branchHint":"Una versión por rama; RC solo si aún no existe una versión final.","emptyDefault":"vacío = sin valor predeterminado","proxyTip":"Proxy HTTP/HTTPS usado por uv, descargas de Python e índices de paquetes.","privateRepoTip":"Índices privados Nexus, Artifactory o compatibles con PyPI.","simpleTip":"URL de índice Simple / PEP 503 usada para instalar paquetes.","browseTip":"URL Browse/API opcional para descubrir paquetes cuando “Instalar todo” está activo.","changeType":"Cambiar tipo","confirmToProject":"¿Cambiar este entorno a Proyecto? El venv permanece donde está hasta vincular una carpeta de proyecto.","confirmToShared":"¿Cambiar este entorno a Compartido? Si hay una carpeta de proyecto vinculada, el .venv gestionado por RFPY vuelve a RFPY y se elimina el vínculo.","chooseFolder":"Elegir esta carpeta","newFolder":"Nueva carpeta","cancel":"Cancelar","folderBrowser":"Elegir carpeta","folderName":"Nombre de la nueva carpeta","caUploaded":"Certificado copiado en RFPY","stop":"Detener","stopping":"Deteniendo…","profileExecution":"Ejecución del perfil","importProfile":"Importar requirements.txt / pyproject.toml","importProfileDone":"Perfil importado","binaryFallback":"Fallback a wheel binario tras error Visual C++ / MSVC","binaryFallbackHint":"Tras un error de compilación MSVC, RFPY reintenta solo el paquete que falla con un wheel binario compatible. El modo solo-binario no se impone por defecto.","cleanupCancelledNew":"Limpiar un entorno nuevo cancelado","cleanupCancelledNewHint":"Si RFPY acaba de crear el venv, al cancelar se elimina el entorno incompleto. Nunca se elimina un venv preexistente.","installSafety":"Instalación / cancelación","importWarnings":"Avisos","jobRunning":"Ya hay una operación RFPY en curso.","venvLabel":"Venv","pipList":"Lista de paquetes","package":"Paquete","versionLabel":"Versión","stopped":"RFPY detenido.","configureRepositories":"Configurar repositorios","webPortAuto":"Puerto automático","webPortFixed":"Puerto personalizado","webPortHint":"En modo automático, RFPY selecciona el primer puerto disponible a partir de 8765.","invalidWebPort":"El puerto Web debe estar entre 1 y 65535.","repoEnableHint":"Active los repositorios privados y configure al menos una URL Simple de Nexus/Artifactory.","latestLabel":"última","installedLabel":"instalado","errorLabel":"Error","statusDefault":"predeterminado","statusOk":"OK","statusCompatible":"compatible","statusBundled":"incluido","statusError":"error","statusIncompatible":"incompatible","categoryPythonSupport":"Soporte Python","categoryWeb":"Web","categoryAPI":"API","categoryData":"Datos","categoryDatabase":"Base de datos","categorySystem":"Sistema","categoryDocuments":"Documentos","categoryMobile":"Móvil","categoryDesktop":"Escritorio","categoryRPA":"RPA / Escritorio","categoryFilesArchive":"Archivos / Ficheros","categoryMessaging":"Mensajería","categoryAILLM":"IA / LLM","settingsHint":"Todos los parámetros de esta página se guardan juntos. Guárdelos antes de salir.","publicPyPIHelp":"Activa o desactiva el índice público de PyPI. La URL Simple / PEP 503 mostrada se transmite a uv/pip.","privateRepositoriesHelp":"Los repositorios internos son opcionales. Se pueden activar varios a la vez; la prioridad determina su orden. Todo repositorio activo debe tener una URL Simple / PEP 503.","privateReposEmpty":"No hay repositorios privados configurados.","proxySectionHelp":"Proxy HTTP/HTTPS usado por uv, Python y las descargas. NO_PROXY excluye hosts locales o internos.","caSectionHelp":"Certificado PEM/CRT adicional para repositorios o proxys TLS de empresa. Déjelo vacío para usar los certificados del sistema.","webPortSectionHelp":"El modo automático evita colisiones entre consolas locales seleccionando el primer puerto libre desde 8765.","installSafetyHelp":"Controla el fallback de wheel binario MSVC y la limpieza de nuevos entornos cancelados.","versionFiltersHelp":"Limita las versiones propuestas por la interfaz sin impedir introducir una versión exacta.","defaultsHelp":"Valores predefinidos al crear un nuevo entorno.","unsavedSettingsQuit":"Hay parámetros modificados sin guardar. ¿Salir y perder estos cambios?","unsavedChanges":"Cambios sin guardar","enabledRepoNeedsUrl":"Un repositorio activo debe tener una URL Simple / PEP 503: ","invalidRepoUrl":"URL de repositorio no válida (se espera http:// o https://): "},"zh":{"subtitle":"Python + Robot Framework 环境","quit":"退出","envs":"环境","installTab":"安装","profilesTab":"配置与库","settings":"设置","refresh":"刷新","content":"所选虚拟环境","activateHint":"激活会修改当前 shell：rfpy 或 rfpy activate 名称。","newEnv":"新环境","name":"名称","baseProfile":"技术基础","installProfile":"库配置","project":"项目 — 推荐","projectHint":"仅用于一个项目。项目目录可以现在或稍后关联。","shared":"共享","sharedHint":"可复用环境。uv pip 使用活动 venv；项目命令受到保护。","projectFolder":"项目目录","browse":"浏览…","clear":"清除","projectPending":"可选。未选择目录时，项目 venv 先保存在 RFPY 中，之后可再关联。","existing":"如果 .venv 已存在","useExisting":"使用现有环境（推荐）","recreate":"重新创建","fail":"停止","pythonVersion":"Python 版本","rfVersion":"Robot Framework 版本","customVersion":"输入版本…","noRf":"不安装","latest":"最新稳定版","install":"安装","execution":"执行","quickTest":"快速验证","runTest":"运行测试","headless":"无头模式","testUrl":"测试 URL","targetEnv":"目标环境","targetHint":"库将安装到“环境”页中选中的环境。","librariesProfiles":"Robot Framework 库 / 安装配置","profile":"配置","loadProfile":"加载配置","saveProfile":"保存选择为配置","deleteProfile":"删除配置","merge":"添加","replace":"替换","mergeHint":"添加会补充当前选择；替换会仅保留加载的配置。","filter":"筛选","extra":"额外库","installSelection":"安装所选","exports":"可复现文件","exportsHint":"生成用于复现、文档和审计的文件，生成后可直接打开。","generate":"生成","open":"打开","projectPath":"项目目录","link":"关联","change":"更改","duplicate":"复制","rename":"重命名","delete":"删除","setDefault":"设为默认","privateRepos":"私有 / 企业仓库","privateReposHint":"启用下方配置的私有仓库。仅使用公共 PyPI 时请保持未选中。","addRepository":"添加仓库","repositoriesHint":"对于 Nexus/Artifactory，至少填写 uv/pip 使用的 Simple / PEP 503 URL。","privateRepoMissing":"只有在添加至少一个已启用且具有 Simple URL 的 Nexus、Artifactory 或 Generic 仓库后，才能启用私有仓库。","publicPyPI":"允许公共 PyPI","proxy":"使用代理","proxyUrl":"代理 URL","noProxy":"NO_PROXY","customCA":"自定义 CA 证书","caHint":"Python、requests、Node 和下载所使用的 PEM/CRT TLS 证书。留空使用系统证书。","repositories":"仓库 / Python 索引","repoName":"名称","repoType":"类型","simpleUrl":"Simple URL","browseUrl":"Browse/API URL","enabled":"启用","installAll":"全部安装","strict":"严格","priority":"优先级","recentVersions":"建议版本","recentPython":"仅显示较新的 Python 分支","recentRobot":"仅显示较新的 Robot Framework","recentHint":"仅在测试旧环境时取消。始终可以输入精确版本。","defaults":"默认值","webPort":"Web 端口","save":"保存","doctor":"Doctor","selectedPython":"环境 Python","language":"语言","noProject":"未关联","confirmChangeProject":"更改项目目录会把 RFPY .venv 移到新项目。继续吗？","duplicateName":"新环境名称","duplicateHint":"RFPY 根据包快照重新创建 venv，并复用 uv 缓存。项目目录会清空。","profileName":"配置名称","noneProfile":"无配置","pythonSupport":"Python 支持依赖","rfLibraries":"Robot Framework 库","badName":"名称缺失或无效。","needPython":"请选择 Python 版本。","needRf":"请选择 Robot Framework 版本。","saved":"已保存","status":"状态","path":"路径","type":"类型","projectShort":"项目","sharedShort":"共享","reqDesc":"已安装依赖项的快照。","pyprojectDesc":"包含依赖项和 Python 版本的现代项目基础文件。","sbomDesc":"Python、npm、CPython、uv 及依赖关系。","branchHint":"每个分支仅显示一个版本；没有正式版时才显示 RC。","emptyDefault":"留空 = 无默认值","proxyTip":"供 uv、Python 下载和包索引使用的 HTTP/HTTPS 代理。","privateRepoTip":"私有 Nexus、Artifactory 或兼容 PyPI 的索引。","simpleTip":"用于安装包的 Simple / PEP 503 索引 URL。","browseTip":"启用“全部安装”时用于发现包的可选 Browse/API URL。","changeType":"更改类型","confirmToProject":"将此环境切换为项目类型？在关联项目目录之前，venv 保持当前位置。","confirmToShared":"将此环境切换为共享类型？如果已关联项目目录，RFPY 管理的 .venv 将移回 RFPY，并清除项目关联。","chooseFolder":"选择此目录","newFolder":"新建目录","cancel":"取消","folderBrowser":"选择目录","folderName":"新目录名称","caUploaded":"证书已复制到 RFPY","stop":"停止","stopping":"正在停止…","profileExecution":"配置执行","importProfile":"导入 requirements.txt / pyproject.toml","importProfileDone":"配置已导入","binaryFallback":"Visual C++ / MSVC 错误时使用二进制 wheel 回退","binaryFallbackHint":"发生 MSVC 编译错误后，RFPY 仅对失败的软件包尝试兼容的二进制 wheel。默认不会强制所有包使用二进制模式。","cleanupCancelledNew":"清理已取消的新环境","cleanupCancelledNewHint":"如果 venv 是 RFPY 刚创建的，取消时会删除不完整环境。已有 venv 永远不会被删除。","installSafety":"安装 / 取消","importWarnings":"警告","jobRunning":"已有 RFPY 操作正在运行。","venvLabel":"虚拟环境","pipList":"软件包列表","package":"软件包","versionLabel":"版本","stopped":"RFPY 已停止。","configureRepositories":"配置仓库","webPortAuto":"自动端口","webPortFixed":"自定义端口","webPortHint":"自动模式下，RFPY 从 8765 开始选择第一个可用端口。","invalidWebPort":"Web 端口必须在 1 到 65535 之间。","repoEnableHint":"启用私有仓库后，请至少配置一个 Nexus/Artifactory Simple URL。","latestLabel":"最新","installedLabel":"已安装","errorLabel":"错误","statusDefault":"默认","statusOk":"正常","statusCompatible":"兼容","statusBundled":"内置","statusError":"错误","statusIncompatible":"不兼容","categoryPythonSupport":"Python 支持","categoryWeb":"Web","categoryAPI":"API","categoryData":"数据","categoryDatabase":"数据库","categorySystem":"系统","categoryDocuments":"文档","categoryMobile":"移动端","categoryDesktop":"桌面","categoryRPA":"RPA / 桌面","categoryFilesArchive":"文件 / 归档","categoryMessaging":"消息","categoryAILLM":"AI / LLM","settingsHint":"此页面的所有设置会一起保存。退出前请先保存。","publicPyPIHelp":"启用或禁用公共 PyPI 索引。此处的 Simple / PEP 503 URL 会传递给 uv/pip。","privateRepositoriesHelp":"内部仓库是可选的。可以同时启用多个仓库；优先级决定其顺序。每个已启用仓库都必须具有 Simple / PEP 503 URL。","privateReposEmpty":"尚未配置私有仓库。","proxySectionHelp":"供 uv、Python 和下载使用的 HTTP/HTTPS 代理。NO_PROXY 用于排除本地或内部主机。","caSectionHelp":"企业 TLS 仓库或代理使用的附加 PEM/CRT 证书。留空则使用系统证书。","webPortSectionHelp":"自动模式从 8765 开始选择第一个可用端口，以避免本地控制台端口冲突。","installSafetyHelp":"控制 MSVC 二进制 wheel 回退以及取消新环境后的清理。","versionFiltersHelp":"限制界面中建议的版本，但仍可输入精确版本。","defaultsHelp":"创建新环境时预填的默认值。","unsavedSettingsQuit":"设置已修改但尚未保存。退出并丢弃这些更改吗？","unsavedChanges":"未保存的更改","enabledRepoNeedsUrl":"已启用的仓库必须具有 Simple / PEP 503 URL：","invalidRepoUrl":"仓库 URL 无效（应为 http:// 或 https://）："}};let lang='fr',state=null,versions=null,selected='',catalog=null,job=null,jobKind='',exportPaths={};const $=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const t=k=>(L[lang]||L.fr)[k]||L.fr[k]||k;
function applyLang(){document.documentElement.lang=lang;document.querySelectorAll('[data-i]').forEach(e=>e.textContent=t(e.dataset.i));document.querySelectorAll('[data-ti]').forEach(e=>e.title=t(e.dataset.ti));document.querySelectorAll('[data-ph-i]').forEach(e=>e.placeholder=t(e.dataset.phI));if(state)renderAll();if(catalog)renderCatalog();if($('doctor')?.classList.contains('active'))loadDoctor();}
function toggleLangMenu(){$('langMenu').classList.toggle('open')} async function setLang(v){lang=v;$('langMenu').classList.remove('open');if(state){state.config.ui=state.config.ui||{};state.config.ui.language=v;await api('/api/language',{method:'POST',body:JSON.stringify({language:v})});await refreshAll();return}applyLang()}
async function api(url,opt={}){opt.headers={'Content-Type':'application/json',...(opt.headers||{})};if(!opt.method||String(opt.method).toUpperCase()==='GET')opt.cache='no-store';let r=await fetch(url,opt),j=await r.json();if(!r.ok)throw new Error(j.error||r.statusText);return j}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));b.classList.add('active');$(b.dataset.page).classList.add('active');if(b.dataset.page==='doctor')loadDoctor();if(b.dataset.page==='profiles')loadCatalog()});
const STATUS_KEYS={default:'statusDefault',ok:'statusOk',compatible:'statusCompatible',bundled:'statusBundled',error:'statusError',incompatible:'statusIncompatible'};function badge(x){let c=x==='ok'||x==='compatible'||x==='bundled'?'ok':x==='error'||x==='incompatible'?'bad':'warn',label=STATUS_KEYS[x]?t(STATUS_KEYS[x]):x;return `<span class="badge ${c}">${esc(label)}</span>`}
async function refreshAll(){state=await api('/api/state');lang=(state.config.ui&&state.config.ui.language)||'fr';versions=await api('/api/versions');$('version').textContent='v'+state.version+' · '+state.home;if(!selected||!state.envs.some(e=>e.name===selected))selected=state.config.default_environment&&state.envs.some(e=>e.name===state.config.default_environment)?state.config.default_environment:(state.envs[0]?.name||'');renderAll();await loadDetails();renderVersionLists();await testEnvChanged();applyLang()}
function renderAll(){renderEnvs();renderSettings();renderProfiles();renderTestEnvs();}
function renderEnvs(){if(!state)return;let rows=state.envs.map(e=>{let path=e.project_path?`<div class="pathcell">${esc(e.project_path)}</div>`:`<span class="muted">${t('noProject')}</span>`;let pb=e.environment_type==='project'?`<button onclick="event.stopPropagation();chooseEnvProject('${esc(e.name)}')">${e.project_path?t('change'):t('link')}</button>`:'';let typeBadge=e.environment_type==='project'?'<span class="badge ok">'+t('projectShort')+'</span>':'<span class="badge warn">'+t('sharedShort')+'</span>';let typeSwitch=` <button title="${t('changeType')}" onclick="event.stopPropagation();changeEnvType('${esc(e.name)}')" style="padding:3px 7px">⇄</button>`;return `<tr class="${e.name===selected?'sel':''}" onclick="selectEnv('${esc(e.name)}')"><td>${e.name===selected?'●':'○'} <b>${esc(e.name)}</b>${e.default?' '+badge('default'):''}</td><td>${typeBadge}${typeSwitch}</td><td>${esc(e.profile)}</td><td>${esc(e.python)}</td><td>${esc(e.robot||'-')}</td><td>${path}${pb}</td><td><button title="${t('setDefault')}" onclick="event.stopPropagation();setDefault('${esc(e.name)}')">★</button><button title="${t('rename')}" onclick="event.stopPropagation();renameEnv('${esc(e.name)}')">✎</button><button title="${t('duplicate')}" onclick="event.stopPropagation();duplicateEnv('${esc(e.name)}')">⧉</button><button class="danger" title="${t('delete')}" onclick="event.stopPropagation();deleteEnv('${esc(e.name)}')">×</button></td></tr>`}).join('');$('envTable').innerHTML=`<table><tr><th>${t('name')}</th><th>${t('type')}</th><th>${t('baseProfile')}</th><th>Python</th><th>RF</th><th>${t('projectPath')}</th><th></th></tr>${rows||'<tr><td colspan="7">—</td></tr>'}</table>`}
async function selectEnv(n){selected=n;renderEnvs();await loadDetails();renderProfiles();renderTestEnvs();await testEnvChanged()}
async function loadDetails(){if(!selected){$('envSummary').textContent='—';$('pipList').innerHTML='';return}let d=await api('/api/env-details?env='+encodeURIComponent(selected));let m=d.manifest;$('envSummary').innerHTML=`<b>${esc(selected)}</b> · ${m.environment_type==='project'?t('project'):t('shared')} · ${esc(m.profile)} · Python ${esc(m.python_resolved||'')} · RF ${esc(m.robot_resolved||'-')}<br>${m.project_path?esc(m.project_path)+'<br>':''}${t('venvLabel')}: ${esc(m.venv||'')}<br>uv ${esc(d.uv.version)} — ${esc(d.uv.path)}<br><span class="muted">${esc(d.note)}</span>`;$('pipList').innerHTML=`<h3 style="margin-top:18px">${t('pipList')}</h3><table><tr><th>${t('package')}</th><th>${t('versionLabel')}</th></tr>${d.packages.map(p=>`<tr><td>${esc(p.name)}</td><td>${esc(p.version)}</td></tr>`).join('')}</table>`}
async function exportEnv(kind){if(!selected)return;let r=await api('/api/export',{method:'POST',body:JSON.stringify({name:selected,kind})});exportPaths[kind]=r.path;$('path-'+kind).textContent=r.path;$('open-'+kind).classList.remove('hidden')} async function openExport(kind){if(exportPaths[kind])await api('/api/open-file',{method:'POST',body:JSON.stringify({path:exportPaths[kind]})})}
async function chooseEnvProject(name){let env=state.envs.find(e=>e.name===name);if(env?.project_path&&!confirm(t('confirmChangeProject')))return;openFolderBrowser(env?.project_path||'',async path=>{try{await api('/api/project-path',{method:'POST',body:JSON.stringify({name,project_path:path})});await refreshAll()}catch(e){alert(e.message)}})}
async function changeEnvType(name){let env=state.envs.find(e=>e.name===name);if(!env)return;let target=env.environment_type==='project'?'shared':'project';let msg=target==='project'?t('confirmToProject'):t('confirmToShared');if(!confirm(msg))return;await api('/api/environment-type',{method:'POST',body:JSON.stringify({name,environment_type:target})});await refreshAll()}
async function duplicateEnv(name){if(job)return alert(t('jobRunning'));let x=prompt(t('duplicateName'),name+'-copy');if(!x)return;if(!confirm(t('duplicateHint')))return;let r=await api('/api/duplicate',{method:'POST',body:JSON.stringify({source:name,new_name:x})});job=r.job;jobKind='install';document.querySelector('[data-page="install"]').click();$('jobLog').textContent='...';poll()}
async function setDefault(n){await api('/api/default',{method:'POST',body:JSON.stringify({name:n})});refreshAll()} async function renameEnv(n){let x=prompt(t('rename'),n);if(!x||x===n)return;await api('/api/rename',{method:'POST',body:JSON.stringify({old:n,new:x})});if(selected===n)selected=x;refreshAll()} async function deleteEnv(n){if(job)return alert(t('jobRunning'));if(!confirm(t('delete')+' '+n+' ?'))return;let r=await api('/api/delete',{method:'POST',body:JSON.stringify({name:n})});job=r.job;jobKind='install';document.querySelector('[data-page="install"]').click();poll()}
function renderVersionLists(){if(!versions)return;let py=$('iPython').value,rf=$('iRobot').value,ip=$('iInstallProfile').value;$('iPython').innerHTML=['<option value="">— '+t('pythonVersion')+' —</option>',...versions.python.map(x=>`<option value="${x.version}">${x.branch} → ${x.version}${x.kind==='rc'?' (RC)':''}</option>`),`<option value="__custom__">${t('customVersion')}</option>`].join('');$('iRobot').innerHTML=[`<option value="">— ${t('noRf')} —</option>`,`<option value="latest">${t('latest')}</option>`,...versions.robot.map(x=>`<option value="${x.version}">${x.branch} → ${x.version}</option>`),`<option value="__custom__">${t('customVersion')}</option>`].join('');let profiles=state?.config?.installation_profiles||{};$('iInstallProfile').innerHTML=`<option value="">— ${t('noneProfile')} —</option>`+Object.keys(profiles).sort().map(n=>`<option>${esc(n)}</option>`).join('');if(py&&[...$('iPython').options].some(o=>o.value===py))$('iPython').value=py;if(rf&&[...$('iRobot').options].some(o=>o.value===rf))$('iRobot').value=rf;if(ip)$('iInstallProfile').value=ip;pyChanged();rfChanged();baseProfileChanged();envTypeChanged()}
function pyChanged(){$('pyExactBox').classList.toggle('hidden',$('iPython').value!=='__custom__')} function rfChanged(){$('rfExactBox').classList.toggle('hidden',$('iRobot').value!=='__custom__')}
function currentEnvType(){return document.querySelector('input[name="envType"]:checked')?.value||'project'} function envTypeChanged(){$('projectBox').classList.toggle('hidden',currentEnvType()!=='project')} function pickInstallProject(){openFolderBrowser($('iProject').value,path=>{$('iProject').value=path;probeProject()})} function clearInstallProject(){$('iProject').value='';$('projectProbe').textContent=t('projectPending');$('existingBox').classList.add('hidden')} async function probeProject(){let p=$('iProject').value.trim();if(!p)return clearInstallProject();let d=await api('/api/project-probe?path='+encodeURIComponent(p));let flags=[d.exists?'folder ✓':'folder +',d.pyproject?'pyproject ✓':'pyproject —',d.uv_lock?'uv.lock ✓':'uv.lock —',d.venv?'.venv ✓ Python '+(d.python||'?'):'.venv —'];$('projectProbe').textContent=flags.join(' · ');$('existingBox').classList.toggle('hidden',!d.venv)} function baseProfileChanged(){let p=$('iProfile').value;if(p==='python'){$('iRobot').value='';$('iRobot').disabled=true;$('rfExactBox').classList.add('hidden')}else{$('iRobot').disabled=false;rfChanged()}}
async function installEnv(){if(job)return alert(t('jobRunning'));$('installError').textContent='';let n=$('iName').value.trim(),profile=$('iProfile').value,py=$('iPython').value==='__custom__'?$('iPythonExact').value.trim():$('iPython').value,rf=$('iRobot').value==='__custom__'?$('iRobotExact').value.trim():$('iRobot').value,environment_type=currentEnvType(),project_path=$('iProject').value.trim(),existing_action=$('iExisting').value,installation_profile=$('iInstallProfile').value;if(!n||/[<>:"/\\|?*]/.test(n))return $('installError').textContent=t('badName');if(!py)return $('installError').textContent=t('needPython');if(profile!=='python'&&!rf)return $('installError').textContent=t('needRf');try{let r=await api('/api/install',{method:'POST',body:JSON.stringify({name:n,profile,python:py,robot:rf,environment_type,project_path,existing_action,installation_profile})});job=r.job;jobKind='install';$('jobLog').textContent='...';setStopButtons(true);poll()}catch(e){$('installError').textContent=e.message}}
function setStopButtons(active){$('stopInstallJob')?.classList.toggle('hidden',!(active&&jobKind==='install'));$('stopProfileJob')?.classList.toggle('hidden',!(active&&jobKind==='packages'))} async function stopCurrentJob(){if(!job)return;setStopButtons(false);try{await api('/api/jobs/cancel',{method:'POST',body:JSON.stringify({job})})}catch(e){alert(e.message)}} async function poll(){if(!job)return;let j=await api('/api/jobs/'+job),target=jobKind==='test'?'testLog':jobKind==='packages'?'profileJobLog':'jobLog';$(target).textContent=(j.logs||[]).join('\n');let active=['running','cancelling'].includes(j.status);setStopButtons(active);if(active)return setTimeout(poll,650);if(j.status==='error'&&jobKind==='install')$('installError').textContent=j.error||t('errorLabel');if(j.status==='done'&&j.result?.name)selected=j.result.name;job=null;jobKind='';setStopButtons(false);await refreshAll()}
function renderTestEnvs(){if(!state)return;$('testEnv').innerHTML=state.envs.map(e=>`<option value="${esc(e.name)}">${esc(e.name)}</option>`).join('');if(selected)$('testEnv').value=selected} async function testEnvChanged(){let n=$('testEnv')?.value;if(!n){$('testWebOptions').classList.add('hidden');return}let d=await api('/api/env-details?env='+encodeURIComponent(n));$('testWebOptions').classList.toggle('hidden',!['playwright','selenium'].includes(d.test_kind))} async function runTest(){if(job)return alert(t('jobRunning'));let n=$('testEnv').value;if(!n)return;let r=await api('/api/test',{method:'POST',body:JSON.stringify({name:n,url:$('testUrl').value,headless:$('testHeadless').checked})});job=r.job;jobKind='test';$('testLog').textContent='...';poll()}
function renderProfiles(){if(!state)return;let e=state.envs.find(x=>x.name===selected);$('pkgEnv').value=selected||'';$('pkgPython').value=e?.python||'';let profiles=state.config.installation_profiles||{};$('installationProfile').innerHTML='<option value=""></option>'+Object.keys(profiles).sort().map(n=>`<option>${esc(n)}</option>`).join('')} async function loadCatalog(){if(!selected)return;let e=state.envs.find(x=>x.name===selected);catalog=await api('/api/catalog?python='+encodeURIComponent(e?.python||'3.14')+'&env='+encodeURIComponent(selected));renderCatalog()}
const CATEGORY_KEYS={'Python support':'categoryPythonSupport','Web':'categoryWeb','API':'categoryAPI','Data':'categoryData','Database':'categoryDatabase','System':'categorySystem','Documents':'categoryDocuments','Mobile':'categoryMobile','Desktop':'categoryDesktop','RPA / Desktop':'categoryRPA','Files / Archive':'categoryFilesArchive','Messaging':'categoryMessaging','AI / LLM':'categoryAILLM'};const categoryLabel=c=>CATEGORY_KEYS[c]?t(CATEGORY_KEYS[c]):c;function pkgCard(x){return `<div class="pkg"><label><input type="checkbox" class="pkgCheck" value="${esc(x.name)}" style="width:auto" ${x.installed?'checked':''}> <b>${esc(x.label)}</b></label><div class="muted">${esc(x.name)} · ${t('latestLabel')} ${esc(x.version)} · ${t('installedLabel')} ${esc(x.installed||'-')} · Python ${esc(x.requires_python)}</div>${badge(x.compatibility)}</div>`} function renderCatalog(){if(!catalog)return;let f=($('pkgFilter').value||'').toLowerCase(),rf={},py=[];catalog.third_party.filter(x=>!f||(x.label+' '+x.name+' '+x.category).toLowerCase().includes(f)).forEach(x=>{if(x.category==='Python support')py.push(x);else(rf[x.category]??=[]).push(x)});$('pkgCatalog').innerHTML=Object.entries(rf).map(([c,a])=>`<h3>${esc(categoryLabel(c))}</h3><div class="pkggrid">${a.map(pkgCard).join('')}</div>`).join('');$('pySupportCatalog').innerHTML=`<div class="pkggrid">${py.map(pkgCard).join('')}</div>`}
function profileMode(){return document.querySelector('input[name="profileMode"]:checked')?.value||'merge'} function profileExtras(){return $('extraPackages').value.split(/\n+/).map(x=>x.trim()).filter(Boolean)} function loadInstallProfile(){let n=$('installationProfile').value;if(!n)return;let values=[...((state.config.installation_profiles||{})[n]||[])],known=new Set([...document.querySelectorAll('.pkgCheck')].map(x=>x.value));if(profileMode()==='replace'){$('extraPackages').value='';document.querySelectorAll('.pkgCheck').forEach(x=>x.checked=false)}document.querySelectorAll('.pkgCheck').forEach(x=>{if(values.includes(x.value))x.checked=true});let extras=values.filter(x=>!known.has(x)),current=profileMode()==='merge'?profileExtras():[];$('extraPackages').value=[...new Set([...current,...extras])].join('\n')} async function saveInstallProfile(){let n=prompt(t('profileName'),$('installationProfile').value||'');if(!n)return;let vals=[...document.querySelectorAll('.pkgCheck:checked')].map(x=>x.value),extra=profileExtras();state.config.installation_profiles=state.config.installation_profiles||{};state.config.installation_profiles[n]=[...new Set([...vals,...extra])];let r=await api('/api/config',{method:'POST',body:JSON.stringify(state.config)});state.config=r.config;renderProfiles();$('installationProfile').value=n;renderVersionLists()} async function deleteInstallProfile(){let n=$('installationProfile').value;if(!n)return;if(!confirm(t('deleteProfile')+' '+n+' ?'))return;delete state.config.installation_profiles[n];let r=await api('/api/config',{method:'POST',body:JSON.stringify(state.config)});state.config=r.config;renderProfiles();renderVersionLists()} async function importProfileFile(input){let f=input.files?.[0];input.value='';if(!f)return;try{let r=await api('/api/profile/import',{method:'POST',body:JSON.stringify({filename:f.name,content:await f.text()})}),n=prompt(t('profileName'),r.suggested_name||'');if(!n)return;state.config.installation_profiles=state.config.installation_profiles||{};state.config.installation_profiles[n]=r.packages||[];let saved=await api('/api/config',{method:'POST',body:JSON.stringify(state.config)});state.config=saved.config;renderProfiles();renderVersionLists();$('installationProfile').value=n;loadInstallProfile();let msg=t('importProfileDone')+': '+n+' ('+(r.packages||[]).length+')';if((r.warnings||[]).length)msg+='\n\n'+t('importWarnings')+':\n'+r.warnings.join('\n');alert(msg)}catch(e){alert(e.message)}} async function installPackages(){if(job)return alert(t('jobRunning'));if(!selected)return;let vals=[...document.querySelectorAll('.pkgCheck:checked')].map(x=>x.value),extra=profileExtras(),packages=[...new Set([...vals,...extra])];if(!packages.length)return;let r=await api('/api/packages/install',{method:'POST',body:JSON.stringify({name:selected,packages,profile:$('installationProfile').value})});job=r.job;jobKind='packages';$('profileExecution').open=true;$('profileJobLog').textContent='...';setStopButtons(true);poll()}

let fsCallback=null,fsData=null,fsSelected='';
async function openFolderBrowser(initial,callback){fsCallback=callback;fsSelected='';$('fsTitle').textContent=t('folderBrowser');$('folderModal').classList.remove('hidden');let roots=await api('/api/fs/roots');$('fsFavs').innerHTML=[...(roots.favourites||[]),...(roots.roots||[])].map(x=>`<button onclick="fsLoad(${JSON.stringify(x.path).replace(/"/g,'&quot;')})">${esc(x.label)}</button>`).join('');await fsLoad(initial||roots.default)}
function closeFolderBrowser(){$('folderModal').classList.add('hidden');fsCallback=null;fsSelected=''}
async function fsLoad(path){try{fsData=await api('/api/fs/list?path='+encodeURIComponent(path||''));fsSelected=fsData.path;$('fsCurrent').value=fsData.path;$('fsUp').disabled=!fsData.parent;$('fsList').innerHTML=(fsData.directories||[]).map(d=>`<div class="fs-item" ondblclick="fsLoad(${JSON.stringify(d.path).replace(/"/g,'&quot;')})" onclick="fsSelect(${JSON.stringify(d.path).replace(/"/g,'&quot;')},this)"><span class="fs-icon">📁</span><span>${esc(d.name)}</span></div>`).join('')||'<div class="muted" style="padding:16px">—</div>'}catch(e){alert(e.message)}}
function fsSelect(path,el){fsSelected=path;document.querySelectorAll('.fs-item').forEach(x=>x.classList.remove('selected'));el?.classList.add('selected')}
function fsUp(){if(fsData?.parent)fsLoad(fsData.parent)}
function fsRefresh(){if(fsData?.path)fsLoad(fsData.path)}
async function fsNewFolder(){if(!fsData?.path)return;let name=prompt(t('folderName'),'');if(!name)return;let r=await api('/api/fs/mkdir',{method:'POST',body:JSON.stringify({parent:fsData.path,name})});await fsLoad(r.path)}
function fsChooseCurrent(){let chosen=fsSelected||fsData?.path;if(!chosen)return;let cb=fsCallback;closeFolderBrowser();if(cb)cb(chosen)}

let settingsBaseline='',allowUnload=false;
function webPortModeChanged(){let a=$('webPortAuto').checked;$('webPort').disabled=a;onSettingsChanged()}
function isHttpUrl(v){return /^https?:\/\//i.test(String(v||'').trim())}
function repoRowData(d){return {name:d.querySelector('.rn')?.value.trim()||'',type:d.querySelector('.rt')?.value||'generic',simple_url:d.querySelector('.rs')?.value.trim()||'',browse_url:d.querySelector('.rb')?.value.trim()||'',enabled:d.dataset.kind==='pypi'?$('aPublic').checked:!!d.querySelector('.re')?.checked,install_all:d.dataset.kind==='pypi'?false:!!d.querySelector('.ra')?.checked,strict:d.dataset.kind==='pypi'?true:(d.querySelector('.rx')?.checked!==false),priority:Number(d.querySelector('.rp')?.value||500)}}
function addRepoRow(r={name:'Nexus / Artifactory',type:'nexus',simple_url:'',browse_url:'',enabled:false,install_all:false,strict:true,priority:500},kind='private'){
 let d=document.createElement('div');d.className='repo subcard';d.dataset.kind=kind;let pypi=kind==='pypi';
 d.innerHTML=`<div class="repo-fields"><div><label><span data-i="repoName"></span></label><input class="rn" value="${esc(r.name||'')}"></div><div><label><span data-i="repoType"></span></label>${pypi?'<input class="rt" type="hidden" value="pypi"><input value="PyPI" disabled>':'<select class="rt"><option>nexus</option><option>artifactory</option><option>generic</option></select>'}</div><div><label><span data-i="simpleUrl"></span></label><input class="rs" value="${esc(r.simple_url||'')}" data-ti="simpleTip" title="${t('simpleTip')}"></div><div><label><span data-i="browseUrl"></span></label><input class="rb" value="${esc(r.browse_url||'')}" data-ti="browseTip" title="${t('browseTip')}"></div></div><div class="repo-options">${pypi?'':`<label><input class="re" type="checkbox" ${r.enabled?'checked':''}> <span data-i="enabled"></span></label><label><input class="ra" type="checkbox" ${r.install_all?'checked':''}> <span data-i="installAll"></span></label><label><input class="rx" type="checkbox" ${r.strict!==false?'checked':''}> <span data-i="strict"></span></label>`}<label><span data-i="priority"></span> <input class="rp repo-priority" type="number" value="${r.priority??(pypi?1000:500)}"></label>${pypi?'':'<button class="danger" onclick="this.closest(\'.repo\').remove();refreshPrivateRepoEmpty();onSettingsChanged()">×</button>'}</div>`;
 if(!pypi)d.querySelector('.rt').value=r.type||'nexus';(pypi?$('pypiRepo'):$('privateReposList')).appendChild(d);d.querySelectorAll('[data-i]').forEach(e=>e.textContent=t(e.dataset.i));refreshPrivateRepoEmpty();onSettingsChanged();return d
}
function refreshPrivateRepoEmpty(){let box=$('privateReposEmpty');if(box)box.classList.toggle('hidden',!!$('privateReposList')?.querySelector('.repo'))}
function openRepositorySettings(){document.querySelector('#privateRepositoriesSection')?.scrollIntoView({behavior:'smooth',block:'start'})}
function privateRepoToggleChanged(){if($('aEnabled').checked&&!$('privateReposList').querySelector('.repo'))addRepoRow();onSettingsChanged()}
function clearCA(){$('caBundle').value='';onSettingsChanged()}
function currentSettingsForm(){let pypi=$('pypiRepo').querySelector('.repo'),privateRows=[...$('privateReposList').querySelectorAll('.repo')];return {proxy:{enabled:$('pEnabled').checked,url:$('pUrl').value.trim(),no_proxy:$('pNo').value.trim()},artifact:{enabled:$('aEnabled').checked,allow_public_pypi:$('aPublic').checked,ca_bundle:$('caBundle').value.trim()},repositories:[...(pypi?[repoRowData(pypi)]:[]),...privateRows.map(repoRowData)],package_install:{binary_fallback_on_msvc_error:$('binaryFallback').checked},cancellation:{cleanup_new_environment:$('cleanupCancelledNew').checked},defaults:{profile:$('dProfile').value,python:$('dPython').value.trim(),robot:$('dRobot').value.trim()},web:{port:$('webPortAuto').checked?0:Number($('webPort').value||0)},version_filters:{python_recent_only:$('recentPython').checked,robot_recent_only:$('recentRobot').checked,python_min:$('pythonMin').value.trim()||'3.10',robot_min:$('robotMin').value.trim()||'6.0'}}}
function settingsSnapshot(){try{return JSON.stringify(currentSettingsForm())}catch(e){return ''}}
function settingsDirty(){return !!settingsBaseline&&settingsSnapshot()!==settingsBaseline}
function updateSettingsDirtyIndicator(){let e=$('settingsDirty');if(!e)return;e.textContent=settingsDirty()?t('unsavedChanges'):'';if(settingsDirty())$('saved').textContent=''}
function onSettingsChanged(){updateSettingsDirtyIndicator()}
function captureSettingsBaseline(){settingsBaseline=settingsSnapshot();updateSettingsDirtyIndicator()}
function renderSettings(){if(!state)return;let c=state.config;$('pEnabled').checked=!!c.proxy.enabled;$('pUrl').value=c.proxy.url||'';$('pNo').value=c.proxy.no_proxy||'';$('aEnabled').checked=!!c.artifact.enabled;$('caBundle').value=c.artifact.ca_bundle||'';$('binaryFallback').checked=(c.package_install?.binary_fallback_on_msvc_error!==false);$('cleanupCancelledNew').checked=(c.cancellation?.cleanup_new_environment!==false);$('dProfile').value=c.defaults.profile||'playwright';$('dPython').value=c.defaults.python||'';$('dRobot').value=c.defaults.robot||'';let wp=Number(c.web?.port||0);$('webPortAuto').checked=wp<=0;$('webPort').value=wp>0?wp:8765;$('webPort').disabled=wp<=0;let vf=c.version_filters||{};$('recentPython').checked=vf.python_recent_only!==false;$('recentRobot').checked=vf.robot_recent_only!==false;$('pythonMin').value=vf.python_min||'3.10';$('robotMin').value=vf.robot_min||'6.0';let repos=c.repositories||[],pypi=repos.find(r=>String(r.type||'').toLowerCase()==='pypi')||{name:'PyPI',type:'pypi',simple_url:'https://pypi.org/simple',browse_url:'',enabled:true,priority:1000};$('aPublic').checked=(c.artifact.allow_public_pypi!==false)&&(pypi.enabled!==false);$('pypiRepo').innerHTML='';$('privateReposList').innerHTML='';addRepoRow(pypi,'pypi');repos.filter(r=>String(r.type||'').toLowerCase()!=='pypi').forEach(r=>addRepoRow(r,'private'));refreshPrivateRepoEmpty();captureSettingsBaseline()}
function validateRepositories(repos,privateEnabled){for(let r of repos){if(r.enabled&&!r.simple_url){alert(t('enabledRepoNeedsUrl')+(r.name||r.type));return false}if(r.simple_url&&!isHttpUrl(r.simple_url)){alert(t('invalidRepoUrl')+(r.name||r.simple_url));return false}if(r.browse_url&&!isHttpUrl(r.browse_url)){alert(t('invalidRepoUrl')+(r.name||r.browse_url));return false}}if(privateEnabled&&!repos.some(r=>r.type!=='pypi'&&r.enabled&&r.simple_url)){alert(t('privateRepoMissing'));return false}return true}
function pickCA(){$('caFileInput').value='';$('caFileInput').click()}
async function uploadCA(input){let f=input.files?.[0];if(!f)return;let buf=new Uint8Array(await f.arrayBuffer()),bin='';for(let i=0;i<buf.length;i+=0x8000)bin+=String.fromCharCode(...buf.subarray(i,i+0x8000));let r=await api('/api/upload-ca',{method:'POST',body:JSON.stringify({filename:f.name,data_base64:btoa(bin)})});$('caBundle').value=r.path||'';onSettingsChanged();alert(t('caUploaded'))}
async function saveSettings(){let form=currentSettingsForm();if(!validateRepositories(form.repositories,form.artifact.enabled))return;let webPort=form.web.port;if(webPort!==0&&(!Number.isInteger(webPort)||webPort<1||webPort>65535)){alert(t('invalidWebPort'));return}let c=state.config;c.proxy=form.proxy;c.artifact=form.artifact;c.package_install={...(c.package_install||{}),...form.package_install};c.cancellation={...(c.cancellation||{}),...form.cancellation};c.defaults={...c.defaults,...form.defaults};c.web={...c.web,...form.web};c.version_filters=form.version_filters;c.repositories=form.repositories;let r=await api('/api/config',{method:'POST',body:JSON.stringify(c)});state.config=r.config;versions=await api('/api/versions');renderVersionLists();renderSettings();$('saved').textContent=' '+t('saved')}
async function loadDoctor(){let d=await api('/api/doctor');$('doctorTable').innerHTML=`<p>${badge(d.status)}</p><table>${d.checks.map(c=>`<tr><td>${badge(c.level)}</td><td>${esc(c.name)}</td><td>${esc(c.detail)}</td></tr>`).join('')}</table>`} async function quitWeb(){let promptText=settingsDirty()?t('unsavedSettingsQuit'):(t('quit')+' ?');if(!confirm(promptText))return;allowUnload=true;try{await api('/api/shutdown',{method:'POST',body:'{}'})}catch(e){}document.body.innerHTML='<main><div class="card"><h2>'+t('stopped')+'</h2></div></main>';setTimeout(()=>window.close(),200)}
window.addEventListener('click',e=>{if(!e.target.closest('.lang-wrap'))$('langMenu').classList.remove('open')});$('settings').addEventListener('input',onSettingsChanged);$('settings').addEventListener('change',onSettingsChanged);window.addEventListener('beforeunload',e=>{if(!allowUnload&&settingsDirty()){e.preventDefault();e.returnValue=''}});refreshAll().catch(e=>alert(e.message));
</script></body></html>'''


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "RFPY"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def read_json(self) -> dict[str, Any]:
        n = int(self.headers.get("Content-Length", "0") or "0")
        if n > 2_000_000:
            raise RfpyError("Requête trop volumineuse")
        raw = self.rfile.read(n) if n else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        try:
            parsed = urllib.parse.urlsplit(self.path)
            path = parsed.path
            q = urllib.parse.parse_qs(parsed.query)
            if path == "/":
                payload = WEB_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)
            elif path == "/api/state":
                self.send_json({"version": APP_VERSION, "author": AUTHOR, "license": LICENSE_ID, "home": str(HOME), "envs": list_envs(), "config": load_config(), "uv": uv_info()})
            elif path == "/api/versions":
                self.send_json({"python": concise_python_versions(), "robot": concise_robot_versions()})
            elif path == "/api/env-details":
                self.send_json(env_details((q.get("env") or [""])[0]))
            elif path == "/api/project-probe":
                self.send_json(probe_project((q.get("path") or [""])[0]))
            elif path == "/api/fs/roots":
                self.send_json(filesystem_roots())
            elif path == "/api/fs/list":
                self.send_json(filesystem_list((q.get("path") or [""])[0]))
            elif path == "/api/doctor":
                self.send_json(doctor())
            elif path == "/api/catalog":
                self.send_json(compatibility_catalog((q.get("python") or ["3.14.0"])[0], (q.get("env") or [""])[0]))
            elif path.startswith("/api/jobs/"):
                job = JOBS.get(path.rsplit("/", 1)[-1])
                if not job:
                    self.send_json({"error": "Job inconnu"}, 404)
                else:
                    self.send_json(job)
            else:
                self.send_json({"error": "Route inconnue"}, 404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def do_POST(self) -> None:
        try:
            path = urllib.parse.urlsplit(self.path).path
            body = self.read_json()
            if path == "/api/install":
                name = str(body.get("name", ""))
                py = str(body.get("python", "")).strip()
                robot = str(body.get("robot", "")).strip()
                profile = str(body.get("profile", "playwright"))
                env_type = normalize_environment_type(str(body.get("environment_type", "project")))
                project_path = str(body.get("project_path", ""))
                existing_action = str(body.get("existing_action", "use"))
                installation_profile = str(body.get("installation_profile", ""))
                existing_project_venv = env_type == "project" and bool(project_path) and python_executable(project_venv_path(project_path)).exists()
                if not py and not (existing_action == "use" and existing_project_venv):
                    raise RfpyError("Version Python manquante.")
                job = JOBS.create("install", lambda log: install_environment(name, py, robot, profile, log=log, environment_type=env_type, project_path=project_path, existing_action=existing_action, installation_profile=installation_profile))
                self.send_json({"job": job}, 202)
            elif path == "/api/test":
                name=str(body.get("name", "")); url=str(body.get("url", "https://www.google.com")) or "https://www.google.com"; headless=bool(body.get("headless", True))
                job=JOBS.create("test", lambda log: run_smoke_test(name,url,headless,log)); self.send_json({"job":job},202)
            elif path == "/api/packages/install":
                name=str(body.get("name", "")); packages=[str(x) for x in body.get("packages", [])]; profile_name=str(body.get("profile", ""))
                job=JOBS.create("packages", lambda log: install_selected_packages(name,packages,log,profile_name)); self.send_json({"job":job},202)
            elif path == "/api/profile/import":
                filename=str(body.get("filename", "")); content=str(body.get("content", ""))
                if len(content.encode("utf-8")) > 1_500_000:
                    raise RfpyError("Fichier de dépendances trop volumineux (1,5 Mo maximum).")
                self.send_json(parse_profile_dependency_file(filename, content))
            elif path == "/api/jobs/cancel":
                self.send_json(JOBS.cancel(str(body.get("job", ""))))
            elif path == "/api/export":
                name=str(body.get("name", "")); kind=str(body.get("kind", ""))
                if kind=="requirements": p=export_requirements(name)
                elif kind=="pyproject": p=export_pyproject(name)
                elif kind=="sbom": p=generate_sbom(name)
                else: raise RfpyError("Type d export inconnu.")
                self.send_json({"ok":True,"path":str(p)})
            elif path == "/api/project-path":
                name=str(body.get("name", "")); project_path=str(body.get("project_path", ""))
                self.send_json({"ok":True,"manifest":set_environment_project_path(name,project_path)})
            elif path == "/api/environment-type":
                name=str(body.get("name", "")); environment_type=str(body.get("environment_type", ""))
                self.send_json({"ok":True,"manifest":set_environment_type(name,environment_type)})
            elif path == "/api/duplicate":
                source=str(body.get("source", "")); new_name=str(body.get("new_name", ""))
                job=JOBS.create("duplicate", lambda log: duplicate_environment(source,new_name,log)); self.send_json({"job":job},202)
            elif path == "/api/open-file":
                open_local_path(str(body.get("path", ""))); self.send_json({"ok":True})
            elif path == "/api/fs/mkdir":
                self.send_json(filesystem_mkdir(str(body.get("parent") or ""),str(body.get("name") or "")))
            elif path == "/api/upload-ca":
                saved=save_uploaded_ca(str(body.get("filename") or ""),str(body.get("data_base64") or ""))
                self.send_json({"ok":True,"path":saved})
            elif path == "/api/language":
                lang=str(body.get("language") or "fr").lower()
                if lang not in {"fr","en","de","es","zh"}: raise RfpyError("Langue invalide.")
                cfg=load_config(); cfg.setdefault("ui",{})["language"]=lang; save_config(cfg); self.send_json({"ok":True,"language":lang})
            elif path == "/api/delete":
                name = str(body.get("name", ""))
                job = JOBS.create("delete", lambda log: delete_environment(name, log) or {"name": name})
                self.send_json({"job": job}, 202)
            elif path == "/api/rename":
                self.send_json(rename_environment(str(body.get("old", "")), str(body.get("new", ""))))
            elif path == "/api/default":
                set_default_environment(str(body.get("name", "")))
                self.send_json({"ok": True})
            elif path == "/api/config":
                cfg = deep_merge(DEFAULT_CONFIG, body)
                save_config(cfg)
                self.send_json({"ok": True, "config": cfg})
            elif path == "/api/shutdown":
                self.send_json({"ok": True})
                threading.Thread(target=self.server.shutdown, name="rfpy-web-shutdown", daemon=True).start()
            else:
                self.send_json({"error": "Route inconnue"}, 404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 400)


def _web_text(lang: str, key: str, **values: Any) -> str:
    table = {
        "fr": {"running":"RFPY Web v{version} : {url}","stop":"Ctrl+C pour arrêter.","localhost":"Par sécurité, l'interface Web RFPY écoute uniquement sur localhost.","busy":"Le port Web {port} est déjà utilisé. Choisissez le mode automatique ou un autre port."},
        "en": {"running":"RFPY Web v{version}: {url}","stop":"Press Ctrl+C to stop.","localhost":"For security, the RFPY Web UI listens on localhost only.","busy":"Web port {port} is already in use. Choose automatic mode or another port."},
        "de": {"running":"RFPY Web v{version}: {url}","stop":"Mit Ctrl+C beenden.","localhost":"Aus Sicherheitsgründen lauscht die RFPY-Weboberfläche nur auf localhost.","busy":"Web-Port {port} wird bereits verwendet. Wählen Sie den automatischen Modus oder einen anderen Port."},
        "es": {"running":"RFPY Web v{version}: {url}","stop":"Ctrl+C para detener.","localhost":"Por seguridad, la interfaz Web de RFPY solo escucha en localhost.","busy":"El puerto Web {port} ya está en uso. Elija el modo automático u otro puerto."},
        "zh": {"running":"RFPY Web v{version}：{url}","stop":"按 Ctrl+C 停止。","localhost":"为安全起见，RFPY Web 界面仅监听 localhost。","busy":"Web 端口 {port} 已被占用。请选择自动模式或其他端口。"},
    }
    bucket=table.get(lang,table["en"])
    return bucket.get(key,table["en"].get(key,key)).format(**values)


def _create_web_server(host: str, configured_port: int) -> ThreadingHTTPServer:
    if configured_port > 0:
        try:
            return ThreadingHTTPServer((host, configured_port), ApiHandler)
        except OSError as exc:
            raise RfpyError(_web_text(current_language(), "busy", port=configured_port)) from exc
    # Automatic mode: prefer the historical RFPY range, then let Windows choose.
    for candidate in range(8765, 8866):
        try:
            return ThreadingHTTPServer((host, candidate), ApiHandler)
        except OSError:
            continue
    return ThreadingHTTPServer((host, 0), ApiHandler)


def serve_web(host: str | None = None, port: int | None = None, open_browser: bool | None = None) -> None:
    cfg = load_config()
    host = host or str(cfg.get("web", {}).get("host", "127.0.0.1"))
    configured_port = int(cfg.get("web", {}).get("port", 0)) if port is None else int(port)
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise RfpyError(_web_text(current_language(), "localhost"))
    open_browser = cfg.get("web", {}).get("open_browser", True) if open_browser is None else open_browser
    server = _create_web_server(host, configured_port)
    actual_port = int(server.server_address[1])
    url = f"http://127.0.0.1:{actual_port}/"
    lang=current_language()
    print(_web_text(lang, "running", version=APP_VERSION, url=url))
    print(_web_text(lang, "stop"))
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def print_envs() -> None:
    envs = list_envs()
    if not envs:
        print(cli_runtime_text("no_envs"))
        return
    cfg = load_config()
    default = cfg.get("default_environment", "")
    print(f"{cli_runtime_text('name'):<24} {cli_runtime_text('type'):<9} {cli_runtime_text('profile'):<12} {'Python':<12} {cli_runtime_text('robot'):<16} {cli_runtime_text('project')}")
    print("-" * 110)
    for e in envs:
        mark = "*" if e["name"] == default else " "
        typ = cli_runtime_text("project_kind") if e.get("environment_type") == "project" else cli_runtime_text("shared_kind")
        print(f"{mark}{e['name']:<23} {typ:<9} {e['profile']:<12} {e['python']:<12} {e['robot']:<16} {e.get('project_path','')}")



def main(argv: list[str] | None = None) -> int:
    ensure_dirs()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    # Commandes internes utilisées par les wrappers shell. Elles restent hors
    # de l'aide publique afin de garder `rfpy -h` lisible.
    if raw_argv and raw_argv[0] == "env-names":
        for item in list_envs():
            print(item["name"])
        return 0
    if raw_argv and raw_argv[0] == "env-list-json":
        print(json.dumps(list_envs(), ensure_ascii=False))
        return 0
    if raw_argv and raw_argv[0] == "env-info":
        if len(raw_argv) != 2:
            print("[ERREUR] env-info attend un nom.", file=sys.stderr)
            return 2
        try:
            print(json.dumps(load_env(raw_argv[1]), ensure_ascii=False))
            return 0
        except Exception as exc:
            print(f"[ERREUR] {exc}", file=sys.stderr)
            return 2

    if raw_argv and raw_argv[0] == "env-shell-tsv":
        if len(raw_argv) != 2:
            print("env-shell-tsv expects an environment name", file=sys.stderr)
            return 2
        try:
            m=load_env(raw_argv[1])
            venv=str(m.get("venv") or "")
            env_type=normalize_environment_type(str(m.get("environment_type") or "shared"))
            project=str(m.get("project_path") or "")
            print(f"{venv}|{env_type}|{project}")
            return 0
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 2

    help_flags = {"-h", "--help", "-help", "/?", "?"}
    if raw_argv and raw_argv[0].lower() == "help":
        print_cli_help(raw_argv[1:])
        return 0
    help_positions = [i for i, token in enumerate(raw_argv) if str(token).lower() in help_flags]
    if help_positions:
        pos = help_positions[0]
        print_cli_help(raw_argv[:pos])
        return 0

    # IMPORTANT: l activation doit etre realisee par le wrapper shell afin
    # de modifier le processus PowerShell/cmd courant. Un appel direct du
    # backend Python sans argument ne doit donc jamais se rabattre silencieusement
    # sur `list`, sinon un probleme de resolution de commande devient invisible.
    if not raw_argv:
        if not list_envs():
            print("[RFPY] " + cli_runtime_text("first_run"))
            serve_web()
            return 0
        print("[RFPY] " + cli_runtime_text("direct_backend"), file=sys.stderr)
        print(f"         La commande `rfpy` doit resoudre vers {BIN_DIR / 'rfpy.ps1'} (PowerShell) ou rfpy.cmd (cmd).", file=sys.stderr)
        print("         Verifiez avec: Get-Command rfpy -All", file=sys.stderr)
        return 2

    parser = argparse.ArgumentParser(
        prog="rfpy",
        description="RFPY - gestionnaire d'environnements Python + Robot Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""TYPES D'ENVIRONNEMENTS
  Projet (recommandé pour le développement)
    Lié à un seul projet. Le venv est <projet>/.venv.
    RFPY positionne UV_PROJECT : uv add/sync/run/build travaillent sur ce projet.

  Partagé
    Venv réutilisable sous RFPY/stacks. Utiliser uv pip pour ses packages.
    RFPY protège uv add/remove/sync/lock/export/build/publish pour éviter
    de synchroniser par erreur un projet courant dans ce venv partagé.

EXEMPLES
  rfpy                         Sélection/activation rapide
  rfpy -m                      Menu de gestion
  rfpy project add C:\\dev\\demo --python 3.14
  rfpy install RF-TOOLS --type shared --python 3.14 --robot latest --profile robot
  rfpy types                   Explication détaillée des deux types
  rfpy web                     Console Web locale
"""
    )
    parser.add_argument("--version", action="version", version=APP_VERSION)
    parser.add_argument("-m", "--menu", action="store_true", help="Menu interactif de gestion (via la commande rfpy)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="Lister les environnements")
    a = sub.add_parser("activate", aliases=["on"], help="Activer un environnement dans le shell courant")
    a.add_argument("name")
    sub.add_parser("deactivate", aliases=["off"], help="Désactiver l'environnement RFPY courant")
    sub.add_parser("status", help="Afficher l'environnement courant")
    d = sub.add_parser("doctor", help="Diagnostiquer RFPY")
    d.add_argument("--json", action="store_true")
    w = sub.add_parser("web", help="Ouvrir l'interface Web locale")
    w.add_argument("--port", type=int)
    w.add_argument("--no-browser", action="store_true")
    i = sub.add_parser("install", help="Installer un environnement")
    i.add_argument("name")
    i.add_argument("--python", default=None)
    i.add_argument("--robot", default=None)
    i.add_argument("--profile", choices=["python", "robot", "playwright", "selenium"], default=None)
    i.add_argument("--type", dest="environment_type", choices=["project", "shared"], default=None, help="project=un seul projet; shared=venv réutilisable")
    i.add_argument("--project", dest="project_path", default="", help="dossier du projet pour --type project")
    i.add_argument("--existing", choices=["use", "recreate", "fail"], default="use", help="si <projet>/.venv existe déjà")
    i.add_argument("--install-profile", default="", help="profil de bibliothèques à appliquer après le socle")
    r = sub.add_parser("rename", help="Renommer un environnement")
    r.add_argument("old")
    r.add_argument("new")
    x = sub.add_parser("delete", help="Supprimer un environnement")
    x.add_argument("name")
    f = sub.add_parser("default", help="Définir l'environnement par défaut")
    f.add_argument("name")
    p = sub.add_parser("packages", help="Lister les packages d'un environnement")
    p.add_argument("name")
    ap=sub.add_parser("add-packages", help="Installer des packages dans un environnement"); ap.add_argument("name"); ap.add_argument("packages",nargs="+")
    ex=sub.add_parser("export", help="Générer requirements.txt, pyproject.toml ou SBOM"); ex.add_argument("name"); ex.add_argument("kind",choices=["requirements","pyproject","sbom"])
    st=sub.add_parser("test", help="Lancer un smoke test adapté à l'environnement"); st.add_argument("name"); st.add_argument("--url",default="https://www.google.com"); st.add_argument("--headed",action="store_true",help="afficher le navigateur")
    dup=sub.add_parser("duplicate", help="Dupliquer un environnement via un snapshot de packages et le cache uv"); dup.add_argument("source"); dup.add_argument("new_name")
    link=sub.add_parser("project-link", help="Associer/changer le dossier projet d'un environnement Projet"); link.add_argument("name"); link.add_argument("project_path")
    ctype=sub.add_parser("type", help="Changer le type d'un environnement: project ou shared"); ctype.add_argument("name"); ctype.add_argument("environment_type", choices=["project","shared"])
    types_p = sub.add_parser("types", help="Expliquer Projet vs Partagé")
    project_p = sub.add_parser("project", help="Adopter/créer un environnement lié à un projet")
    project_sub = project_p.add_subparsers(dest="project_command")
    project_add = project_sub.add_parser("add", help="Ajouter/adopter un projet existant")
    project_add.add_argument("path")
    project_add.add_argument("--name", default="")
    project_add.add_argument("--python", default=None)
    project_add.add_argument("--robot", default=None)
    project_add.add_argument("--profile", choices=["python", "robot", "playwright", "selenium"], default="python")
    project_add.add_argument("--existing", choices=["use", "recreate", "fail"], default="use")
    c = sub.add_parser("config", help="Afficher le fichier de configuration")
    c.add_argument("action", choices=["show", "path"], nargs="?", default="show")
    lng = sub.add_parser("language", aliases=["lang"], help="Afficher ou modifier la langue CLI/Web")
    lng.add_argument("language", nargs="?", choices=list(SUPPORTED_LANGUAGES))

    args = parser.parse_args(raw_argv)
    if args.menu:
        print(cli_runtime_text("menu_wrapper"))
        return 0
    cmd = args.command
    try:
        if cmd == "list":
            print_envs()
        elif cmd in {"activate", "on", "deactivate", "off"}:
            raise RfpyError(cli_runtime_text("wrapper_required"))
        elif cmd == "status":
            active = os.environ.get("RFPY_ENV", "")
            print(active if active else cli_runtime_text("no_active"))
        elif cmd == "doctor":
            rep = doctor()
            if args.json:
                print(json.dumps(rep, indent=2, ensure_ascii=False))
            else:
                print_doctor(rep)
            return 0 if rep["status"] != "error" else 1
        elif cmd == "web":
            serve_web(port=args.port, open_browser=not args.no_browser)
        elif cmd in {"language", "lang"}:
            if args.language:
                lang = set_language(args.language)
                print(f"[RFPY] {CLI_I18N[lang]['lang_saved']}: {LANGUAGE_NAMES[lang]} ({lang})")
            else:
                interactive_language()
        elif cmd == "install":
            cfg = load_config()
            defaults = cfg.get("defaults", {})
            py = args.python if args.python is not None else str(defaults.get("python", "") or "")
            robot = args.robot if args.robot is not None else str(defaults.get("robot", "") or "")
            profile = args.profile or defaults.get("profile", "playwright")
            env_type = args.environment_type or "shared"  # compatibilité CLI historique
            if not py and not (env_type == "project" and args.project_path and args.existing == "use" and python_executable(project_venv_path(args.project_path)).exists()):
                raise RfpyError("Version Python manquante. Utilisez --python VERSION ou adoptez un .venv projet existant.")
            install_environment(args.name, py, robot, profile, environment_type=env_type, project_path=args.project_path, existing_action=args.existing, installation_profile=args.install_profile)
        elif cmd == "rename":
            m = rename_environment(args.old, args.new)
            print(f"[OK] {args.old} -> {m['name']}")
        elif cmd == "delete":
            delete_environment(args.name)
        elif cmd == "default":
            set_default_environment(args.name)
            print("[OK] " + cli_runtime_text("default_set", name=args.name))
        elif cmd == "packages":
            for item in installed_packages(args.name):
                print(f"{item['name']:<35} {item['version']}")
        elif cmd == "add-packages":
            install_selected_packages(args.name,args.packages)
        elif cmd == "export":
            p=export_requirements(args.name) if args.kind=="requirements" else export_pyproject(args.name) if args.kind=="pyproject" else generate_sbom(args.name); print(p)
        elif cmd == "test":
            run_smoke_test(args.name,args.url,not args.headed)
        elif cmd == "duplicate":
            duplicate_environment(args.source,args.new_name)
        elif cmd == "project-link":
            m=set_environment_project_path(args.name,args.project_path); print(json.dumps(m,indent=2,ensure_ascii=False))
        elif cmd == "type":
            m=set_environment_type(args.name,args.environment_type); print(json.dumps(m,indent=2,ensure_ascii=False))
        elif cmd == "types":
            print(cli_runtime_text("types"))
        elif cmd == "project":
            if args.project_command != "add":
                raise RfpyError("Utilisez: rfpy project add CHEMIN")
            pth = Path(args.path).expanduser()
            name = args.name or pth.resolve().name
            cfg = load_config(); defaults = cfg.get("defaults", {})
            py = args.python if args.python is not None else str(defaults.get("python", "") or "")
            robot = args.robot if args.robot is not None else str(defaults.get("robot", "") or "")
            existing_py = python_executable(project_venv_path(pth)).exists()
            if not py and not (args.existing == "use" and existing_py):
                raise RfpyError("Version Python manquante: --python VERSION (sauf si un .venv existant est adopté).")
            install_environment(name, py, robot, args.profile, environment_type="project", project_path=str(pth), existing_action=args.existing)
        elif cmd == "config":
            if args.action == "path":
                print(CONFIG_FILE)
            else:
                print(CONFIG_FILE.read_text(encoding="utf-8"))
        return 0
    except RfpyError as exc:
        print(f"[ERREUR] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[ERREUR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
