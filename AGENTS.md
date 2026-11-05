---
framework_version: 1.0.0
---

# Agent Guidelines: AI Job Search (Antigravity & Argon Edition)

This workspace is natively structured for **Google Antigravity** (and the **Argon** model) to manage job search activities, multi-portal scrapers, 8-criteria matrix extraction, tailored LaTeX CVs, cover letters, and interview preparation.

## Native Antigravity Architecture (Single Source of Truth)

All candidate profiles, workflow specifications, and portal skills live natively under `GEMINI.md` and `.agents/`:

1. **Personal Candidate Profile:**
   - The candidate profile, contact details, education, and target preferences are defined in [GEMINI.md](GEMINI.md) and the individual profile methodology files under [.agents/skills/job-application-assistant/](.agents/skills/job-application-assistant/) (`01-candidate-profile.md` through `09-web-research.md`).
2. **Canonical Workflow Specifications & Commands:**
   - All Antigravity Agent Skills live in [.agents/skills/](.agents/skills/) and are automatically discovered on-demand by Antigravity.
   - Detailed command runbooks (`setup.md`, `apply.md`, `rank.md`, `interview.md`, `outcome.md`, `expand.md`, `reset.md`, `html-report.md`, `gmail-sync.md`, `notion-sync.md`, `add-portal.md`, `add-template.md`) live in [.agents/commands/](.agents/commands/).
   - Specialized subagent prompts (`posting-fetcher.md`, `posting-scorer.md`, `application-reviewer.md`) live in [.agents/subagents/](.agents/subagents/) for use with Antigravity's `invoke_subagent` tool.
3. **Portal Search Skills:**
   - Job-portal search skills live under [.agents/skills/](.agents/skills/):
     - `linkedin-search` (`.agents/skills/linkedin-search/`)
     - `hellowork-search` (`.agents/skills/hellowork-search/`)
     - `freehire-search` (`.agents/skills/freehire-search/`)
     - `apec-indeed-search` (`.agents/skills/apec-indeed-search/` for `apec.fr` and `fr.indeed.com`)
     - *(The 4 Danish demo portals are disabled with `enabled: false`)*

## Configuration Spécifique macOS (`x86_64`) & Matrice Google Sheets

- **Environnement Python & Outils :**
  - Toujours utiliser `.venv/bin/python` (Python 3.12) et `$HOME/.bun/bin/bun` pour exécuter les scripts de `tools/` et les CLIs de `.agents/skills/*/cli/`.
- **Matrice d'Extraction à 8 Critères & Export Google Sheets :**
  - Utiliser `tools/extract_job_matrix.py` (et le skill `job-matrix-extractor`) pour extraire systématiquement :
    1. `Intitulé de l'offre` (`intitule_offre`)
    2. `Entreprise` (`entreprise`)
    3. `Localisation/Télétravail` (`localisation_teletravail`)
    4. `Missions principales` (`missions_principales`)
    5. `Compétences attendues` (`competences_attendues`)
    6. `Outils et technologies` (`outils_technologies`)
    7. `Expérience sectorielle demandée` (`experience_sectorielle`)
    8. `Salaire` (`salaire`)
  - Exports générés automatiquement dans `job_scraper/job_matrix_export.csv` (UTF-8-SIG pour Google Sheets) et `job_scraper/job_matrix_export.json`.
