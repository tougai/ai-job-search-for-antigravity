---
name: job-matrix-extractor
description: >-
  Use this skill whenever the user wants to analyze one or more job postings and
  extract the 8 specific criteria of their evaluation matrix (Intitulé de l'offre,
  Entreprise, Localisation/Télétravail, Missions principales, Compétences attendues,
  Outils et technologies, Expérience sectorielle demandée, Salaire), or export/update
  the structured CSV and JSON files for Google Sheets. Trigger phrases: extraire la
  matrice, analyser cette offre, exporter vers Google Sheets, CSV, JSON, critères de
  la matrice, extract job matrix.
---

# Job Matrix Extractor (8-Criteria Google Sheets Exporter)

This skill extracts and normalizes job offers according to the user's **8-criteria analysis matrix** and exports them into UTF-8-SIG CSV (`job_scraper/job_matrix_export.csv`) and JSON (`job_scraper/job_matrix_export.json`).

## The 8 Required Matrix Criteria

Every analyzed job offer MUST populate these exact 8 fields (plus tracking metadata):

| # | CSV Column Header (Google Sheets) | JSON Key | Content Guidelines |
|---|---|---|---|
| 1 | `Intitulé de l'offre` | `intitule_offre` | Exact job title (cleaned of gender/reference tags if noisy, or kept as posted). |
| 2 | `Entreprise` | `entreprise` | Hiring company or recruitment agency name. |
| 3 | `Localisation/Télétravail` | `localisation_teletravail` | City/Department/Region + remote policy (`Présentiel`, `Hybride / Télétravail partiel`, `Full Remote`, or `Non précisé`). |
| 4 | `Missions principales` | `missions_principales` | Key operational & strategic responsibilities separated by ` ; `. |
| 5 | `Compétences attendues` | `competences_attendues` | Functional, technical, methodological, and soft skills required (` ; ` separated). |
| 6 | `Outils et technologies` | `outils_technologies` | Software, programming languages, cloud platforms, BI/ETL tools, frameworks mentioned. |
| 7 | `Expérience sectorielle demandée` | `experience_sectorielle` | Years of experience required, degree level, and target industry/sector experience. |
| 8 | `Salaire` | `salaire` | Disclosed salary range / package, or `Non communiqué` if absent. |
| *+* | `Score Fit`, `Portail`, `Date d'extraction`, `URL` | `score_fit`, `portail`, `date_extraction`, `url` | Fit score (`0-100` or `High/Medium/Low`), source portal, ISO date, and direct URL. |

## Commands

### 1. Automatic Extraction from a Portal CLI (`detail`)

```bash
export PATH="$PWD/.venv/bin:$HOME/.bun/bin:$PATH"
bun run .agents/skills/hellowork-search/cli/src/cli.ts detail <id_or_url> --format json | \
  python3 tools/extract_job_matrix.py extract --portal "HelloWork" --export
```

### 2. Automatic Extraction from Any Web URL

```bash
export PATH="$PWD/.venv/bin:$HOME/.bun/bin:$PATH"
python3 tools/fetch_page.py "<url>" --text | \
  python3 tools/extract_job_matrix.py extract --title "<Title>" --company "<Company>" --url "<url>" --portal "<Portal>" --export
```

### 3. AI-Enriched Export (Recommended with Argon)

When analyzing one or multiple job postings in conversation, refine the 8 fields for maximum precision, write the JSON array to `/tmp/matrix_batch.json`, and run:

```bash
.venv/bin/python tools/extract_job_matrix.py export --in /tmp/matrix_batch.json
```

This atomically updates:
- `job_scraper/job_matrix_export.csv` (encoded in `utf-8-sig` so Google Sheets and Excel on Mac preserve all French accents)
- `job_scraper/job_matrix_export.json`
