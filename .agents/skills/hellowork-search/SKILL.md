---
name: hellowork-search
version: 1.0.0
description: >
  Use this skill whenever the user wants to search for jobs in France on HelloWork
  (hellowork.com), find French job listings, or look up a specific HelloWork job
  posting. Invoke for open positions, CDI, CDD, freelance, alternance, or remote
  roles in French cities or regions (Paris, Lyon, Marseille, Toulouse, Bordeaux,
  Nantes, Lille, Île-de-France, etc.). Trigger phrases: hellowork, recherche emploi
  france, offres d'emploi, trouver un job, emploi paris, emploi france, cdi,
  télétravail, "offres sur hellowork".
enabled: true
---

# HelloWork Search Skill

Search live job listings from **HelloWork** (`hellowork.com`, major French job board)
with zero runtime dependencies using `bun`.

## ⚠️ Personal use only

HelloWork's `robots.txt` disallows automated crawling of `/fr-fr/emploi/recherche.html`.
This CLI is strictly for **low-volume personal job search use** on your own machine.
Keep query volume low and never use it for commercial or bulk scraping.

## Commands

### Search job listings

```bash
bun run .agents/skills/hellowork-search/cli/src/cli.ts search -q "<keywords>" [-l "<location>"] [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — **required.** Keywords (job title, skill, role).
- `--location <text>` / `-l <text>` — French city, department, or region (e.g. `"Paris"`, `"Lyon"`, `"Île-de-France"`). Optional.
- `--jobage <days>` — posted within N days (`1`, `3`, `7`, `14`, `30`).
- `--page <n>` — 1-indexed page number (default `1`).
- `--limit <n>` / `-n <n>` — cap total results returned.
- `--format json|table|plain` — default `json`.

### Fetch full job detail

```bash
bun run .agents/skills/hellowork-search/cli/src/cli.ts detail <id|url> [--format json|plain]
```

Returns the full description, company, location, contract type, salary (when published), and publication date extracted from the posting's Schema.org `JobPosting` JSON-LD and page markup.

## Usage examples

```bash
# Search Data Engineer roles in Paris
bun run .agents/skills/hellowork-search/cli/src/cli.ts search -q "data engineer" -l "Paris" --limit 5 --format table

# Search Chef de Projet IT roles in Lyon posted within 14 days
bun run .agents/skills/hellowork-search/cli/src/cli.ts search -q "chef de projet IT" -l "Lyon" --jobage 14 --format table

# Fetch full details for a specific offer ID
bun run .agents/skills/hellowork-search/cli/src/cli.ts detail 71820699 --format plain
```
