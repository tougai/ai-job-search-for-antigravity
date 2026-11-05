---
name: job-ranker
description: >-
  Use this skill when the user wants to rank, score, or triage scraped job postings
  (/rank) against their candidate profile and evaluation criteria, producing a
  prioritized shortlist and updating the Google Sheets export. Trigger phrases:
  /rank, classer les offres, scorer les offres, trier les offres, rank jobs,
  shortlist jobs.
---

# Job Ranker (`/rank` for Antigravity)

This skill adapts the canonical [.agents/commands/rank.md](../../commands/rank.md) workflow to run natively on Antigravity with the Argon model.

## Key Antigravity Adaptations

1. **Python Interpreter**: Always run `tools/rank_state.py` using `.venv/bin/python`:
   ```bash
   .venv/bin/python tools/rank_state.py candidates --limit 10
   ```
2. **Subagent Dispatch**: Instead of Antigravity's `Agent` tool, use Antigravity's native `invoke_subagent` tool (`TypeName: "research"`, `Model: "inherit"`) to fetch, run `tools/posting_guard.py`, and score batches of candidate postings in parallel against [.agents/skills/job-application-assistant/04-job-evaluation.md](../job-application-assistant/04-job-evaluation.md).
3. **Write-Back & Matrix Sync**:
   - Apply the scoring results to `job_scraper/seen_jobs.json`:
     ```bash
     .venv/bin/python tools/rank_state.py apply --results /tmp/rank_results.json
     ```
   - Sync the updated `score_fit` into `job_scraper/job_matrix_export.csv` and `job_scraper/job_matrix_export.json` using `tools/extract_job_matrix.py`.
