---
name: apec-indeed-search
description: >-
  Use this skill whenever the user wants to search for jobs on APEC (apec.fr, French
  executive/cadre job board) or Indeed France (fr.indeed.com), or extract job offers
  from APEC and Indeed into the 8-criteria evaluation matrix. Trigger phrases: apec,
  apec.fr, indeed, fr.indeed.com, offres cadre, emploi cadre, chercher sur l'apec,
  chercher sur indeed.
---

# APEC & Indeed France Search Skill

Both **APEC** (`apec.fr`) and **Indeed France** (`fr.indeed.com`) protect their raw search endpoints with JavaScript anti-bot challenges (DataDome on APEC, Cloudflare on Indeed), which return HTTP 403 to plain CLI HTTP requests.

This skill uses Antigravity's native `search_web` tool and `tools/extract_job_matrix.py` to search and extract listings from both portals reliably without requiring paid proxy services or triggering CAPTCHAs.

## Workflow for Searching APEC (`apec.fr`)

1. **Search via `search_web`**:
   Call `search_web` with `domain: "apec.fr"` and a query targeting APEC's detail URLs:
   - Query pattern: `site:apec.fr/candidat/recherche-emploi.html/emploi/detail-offre "<role or keywords>" "<city>"`
   - Example: `site:apec.fr/candidat/recherche-emploi.html/emploi/detail-offre "Data Engineer" "Paris"`
2. **Fetch & Gate Details**:
   - For promising hits, retrieve the full description via `search_web` (searching the exact offer number/title on `apec.fr`) or local Google Chrome if needed.
3. **Extract into the 8-Criteria Matrix**:
   - Populate the 8 matrix fields (`intitule_offre`, `entreprise`, `localisation_teletravail`, `missions_principales`, `competences_attendues`, `outils_technologies`, `experience_sectorielle`, `salaire`) with `portail: "APEC"` and export via:
     ```bash
     .venv/bin/python tools/extract_job_matrix.py export --in /tmp/apec_offers.json
     ```

## Workflow for Searching Indeed France (`fr.indeed.com`)

1. **Search via `search_web`**:
   Call `search_web` with `domain: "fr.indeed.com"` and a query targeting job postings:
   - Query pattern: `site:fr.indeed.com "<role or keywords>" "<city>"`
   - Example: `site:fr.indeed.com "Data Engineer" "Paris" CDI`
2. **Extract into the 8-Criteria Matrix**:
   - Populate the 8 matrix fields with `portail: "Indeed"` and export via:
     ```bash
     .venv/bin/python tools/extract_job_matrix.py export --in /tmp/indeed_offers.json
     ```
