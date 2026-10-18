# Changes

**Copyright © 2026 Olivier RENAULT — Apache-2.0**


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
- Profiles installation now remains in the **Profiles & libraries** tab with a collapsible execution log.
- Import `requirements.txt` or `pyproject.toml` into a reusable RFPY installation profile.
- Optional targeted binary-wheel fallback after explicit Windows MSVC / Visual C++ build failures.
- Installation jobs can be cancelled; newly created incomplete environments can be cleaned safely without deleting a pre-existing project `.venv`.
- Exported files open through a detached launcher so VS Code/Electron diagnostics do not pollute the RFPY Web console terminal.
- Apache-2.0 attribution strengthened with `NOTICE`, `AUTHORS`, UI/SBOM metadata and copyright notices for **Olivier RENAULT**.
