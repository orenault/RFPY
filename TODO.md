# TODO

**Copyright © 2026 Olivier RENAULT — Apache-2.0**


This file tracks deliberately deferred work. It is not a commitment to a specific release date.

## AI / local models

- Add a carefully designed **IA / LLM + Ollama + local model** workflow.
- Compare model sources and download mechanisms, including Ollama registries and Hugging Face.
- Add hardware-aware guidance based on RAM, VRAM, GPU backend and available disk space.
- Let the user choose model storage location before large downloads.
- Add optional Ollama API / inference smoke tests without making them part of basic installation validation.
- Evaluate optional helpers for registering RF-MCP with supported coding agents while keeping configuration changes explicit and reversible.

## Package health

- Enrich the installed-package table with:
  - installed version;
  - latest compatible version;
  - last publication date;
  - update state;
  - known vulnerabilities.
- Keep remote metadata asynchronous and cached so selecting an environment remains immediate.
- Evaluate OSV batch queries for vulnerability information.
- Distinguish direct libraries from transitive dependencies.

## Distribution

- Add Windows code signing when a signing identity is available.
- Publish the stable installer through WinGet after silent-install behavior is fully validated.
- Evaluate Scoop / Chocolatey only if there is community demand.

## Environment management

- Design a transactional rollback for package/profile changes applied to an **existing** environment. Cancellation currently stops the job but deliberately keeps changes already applied rather than attempting a potentially destructive rollback.
- Evaluate richer cancellation policies for project `.venv` recreation, where restoring the pre-existing environment would require an explicit backup/snapshot strategy.
- Improve conflict explanations when a selected project directory is already linked to another environment or already contains a `.venv`.
- Show project-folder ownership directly in the integrated Web folder browser.
- Continue improving reproducibility exports and dependency visualization.

## Platform support

- RFPY 1.0.0 targets Windows. Evaluate Linux / macOS support without weakening the Windows workflow.
