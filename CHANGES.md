# Changes

**Copyright © 2026 Olivier RENAULT — Apache-2.0**


## 1.0.0 - correctifs installateur multilingue (pré-release)

- Localisation étendue aux textes dynamiques de la console Web, aux messages de démarrage `rfpyw` et aux sorties CLI courantes.
- Sélecteur CLI harmonisé PowerShell / `cmd.exe` : navigation clavier, **F2** pour la langue globale, langue courante et environnement actif mis en évidence en vert.
- Activation `cmd.exe` corrigée : les métadonnées d’environnement passent désormais par une sortie interne sûre au lieu d’un `python -c` fragile avec guillemets imbriqués.
- Port Web configurable : mode automatique par défaut (premier port libre à partir de 8765) ou port fixe choisi dans l’installateur / les paramètres Web.
- Configuration Nexus / Artifactory rendue explicite depuis le sélecteur « dépôts privés / d’entreprise », avec accès direct à la saisie des URLs Simple / PEP 503.
- Restauration des actions Web d’environnement (export, changement de projet/type, duplication, renommage, suppression) après réorganisation des sources.
- Remplacement de l'emoji globe WinForms non rendu par un globe dessiné nativement.
- Traduction de toutes les sorties propres à l'installeur selon la langue choisie.
- `rfpy doctor` suit maintenant la langue configurée FR/EN/DE/ES/ZH.
- Forçage UTF-8 de la console PS2EXE / Windows PowerShell et des sorties Python afin d'éviter le mojibake (`désactivé` affiché `dÚsactivÚ`, etc.).
- Les messages provenant directement de `uv` restent ceux de l'outil amont (généralement en anglais).

## 1.0.0

First stable public RFPY release.

Highlights:

- Project and Shared Python / Robot Framework environments powered by uv.
- Local Web console and shell activation workflow.
- Robot Framework library profiles, Browser / Playwright and Selenium support.
- RF-MCP-oriented **IA / LLM** profile.
- Optional **IA / LLM + Ollama** profile; Ollama runtime installation does not download a model.
- Configurable repositories, proxy and custom CA support.
- Requirements / pyproject / CycloneDX export.
- CLI and Web Doctor.
- Native installer directory selection when no `InstallDir` is provided.
- GitHub Actions validation and GitHub Release build pipeline.
- Cleaner public repository layout with runtime sources under `src/`, installer source under `installer/` and visual assets under `assets/`; installed RFPY layout is unchanged.
- Deterministic installer payload embedding across LF/CRLF checkouts and GitHub Actions updated to Node.js 24-compatible action versions.
- Windows PowerShell 5.1 source parsing hardened by storing PowerShell sources as UTF-8 with BOM when they contain non-ASCII text.
- Profiles installation now remains in the **Profiles & libraries** tab with a collapsible execution log.
- Import `requirements.txt` or `pyproject.toml` into a reusable RFPY installation profile.
- Optional targeted binary-wheel fallback after explicit Windows MSVC / Visual C++ build failures.
- Installation jobs can be cancelled; newly created incomplete environments can be cleaned safely without deleting a pre-existing project `.venv`.
- Exported files open through a detached launcher so VS Code/Electron diagnostics do not pollute the RFPY Web console terminal.
- Apache-2.0 attribution strengthened with `NOTICE`, `AUTHORS`, UI/SBOM metadata and copyright notices for **Olivier RENAULT**.
- Native installer branding improved with RFPY icon/logo, version/copyright footer and a five-language selector; the selected language seeds both CLI and Web configuration.
- CLI help unified between PowerShell and `cmd.exe`, including localized command-specific examples such as `rfpy install -h`.
- Quick-selector **Esc** now returns to the shell instead of opening Web; `cmd.exe` no longer mistakes a backend-listing failure for an empty installation.
- Added `rfpy language` / CLI language settings and the direct `rfpyw` shortcut for the Web console.
- Private/enterprise repositories are now opt-in, with explicit Nexus/Artifactory/PEP 503 URL guidance and validation before the setting can be enabled.


- Hotfix Web : restauration des fonctions JavaScript de l'onglet Installation (`currentEnvType`, `envTypeChanged`, sélection du dossier projet) pour corriger la page blanche avec l'erreur `envTypeChanged is not defined`.

- Renforcement du harnais anti-régression : nouveaux tests d'intégrité entre sources Web, `WEB_HTML`, payloads Base64 de l'installeur et handlers JavaScript ; aucun test existant n'est supprimé ni modifié.

- Paramétrage Web : fusion Settings/Repositories dans un bloc unique vertical, sauvegarde remontée en tête, séparation PyPI/dépôts privés, contrôle des URLs des dépôts actifs et avertissement en cas de paramètres non sauvegardés à la fermeture.
- CMD : correction de l'activation d'un environnement ; le message localisé est exécuté avant `endlocal` afin de ne plus perdre le chemin du wrapper PowerShell.
- Tests : ajout d'un nouveau harnais de régression `tests/test_settings_cmd_regressions.py` sans suppression ni modification des tests existants.

- CLI : ajout de F3 pour ouvrir la console Web depuis les menus PowerShell/CMD ; sous CMD, le prompt affiche désormais `[RFPY - ENV]` et `rfpy off` restaure le prompt précédent.
