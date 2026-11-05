#!/usr/bin/env python3
"""Extract the 8-criteria job evaluation matrix and export to CSV/JSON for Google Sheets.

Criteria extracted for every job offer:
  1. Intitulé de l'offre          (intitule_offre)
  2. Entreprise                   (entreprise)
  3. Localisation/Télétravail     (localisation_teletravail)
  4. Missions principales         (missions_principales)
  5. Compétences attendues        (competences_attendues)
  6. Outils et technologies       (outils_technologies)
  7. Expérience sectorielle demandée (experience_sectorielle)
  8. Salaire                      (salaire)

Plus tracking metadata:
  - Score Fit                     (score_fit)
  - Portail                       (portail)
  - Date d'extraction             (date_extraction)
  - URL                           (url)

Usage:
  python3 tools/extract_job_matrix.py extract [--in FILE] [--title TEXT] [--company TEXT] [--location TEXT] [--url URL] [--portal TEXT] [--salary TEXT]
  python3 tools/extract_job_matrix.py export --in batch.json [--csv PATH] [--json PATH] [--append]
  python3 tools/extract_job_matrix.py from-seen [--csv PATH] [--json PATH]
"""

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from posting_guard import guard  # noqa: E402

DEFAULT_CSV = ROOT / "job_scraper" / "job_matrix_export.csv"
DEFAULT_JSON = ROOT / "job_scraper" / "job_matrix_export.json"
SEEN_JOBS = ROOT / "job_scraper" / "seen_jobs.json"

MATRIX_COLUMNS = [
    ("intitule_offre", "Intitulé de l'offre"),
    ("entreprise", "Entreprise"),
    ("localisation_teletravail", "Localisation/Télétravail"),
    ("missions_principales", "Missions principales"),
    ("competences_attendues", "Compétences attendues"),
    ("outils_technologies", "Outils et technologies"),
    ("experience_sectorielle", "Expérience sectorielle demandée"),
    ("salaire", "Salaire"),
    ("score_fit", "Score Fit"),
    ("portail", "Portail"),
    ("date_extraction", "Date d'extraction"),
    ("url", "URL"),
]

# Known technical tools, languages, frameworks, platforms, and software for fallback extraction
KNOWN_TOOLS_RE = re.compile(
    r"\b("
    r"Python|SQL|NoSQL|PostgreSQL|MySQL|Oracle|Snowflake|BigQuery|Redshift|Databricks|Spark|PySpark|"
    r"Airflow|dbt|Kafka|Informatica|Talend|SSIS|SSAS|SSRS|DataStage|Fivetran|Airbyte|"
    r"Power\s*BI|Tableau|Looker|Metabase|Qlik|Excel|VBA|Google\s*Sheets|"
    r"AWS|Azure|GCP|Google\s*Cloud|Docker|Kubernetes|Terraform|Ansible|Jenkins|GitLab\s*CI|GitHub\s*Actions|Git|GitLab|GitHub|"
    r"Java|Scala|C\+\+|C#|Go|Rust|TypeScript|JavaScript|React|Angular|Vue|Node\.?js|Django|FastAPI|Flask|Spring|"
    r"TensorFlow|PyTorch|Scikit-learn|Pandas|NumPy|MLflow|Hugging\s*Face|LangChain|OpenAI|LLM|RAG|"
    r"SAP|Salesforce|Jira|Confluence|Notion|Trello|ServiceNow|Figma|Linux|Bash"
    r")\b",
    re.IGNORECASE,
)

REMOTE_PATTERNS = [
    (re.compile(r"\b(full\s*remote|100\s*%\s*t[éèe]l[éèe]travail|t[éèe]l[éèe]travail\s*complet|t[éèe]l[éèe]travail\s*total)\b", re.I), "Full Remote"),
    (re.compile(r"\b(hybride|hybrid|t[éèe]l[éèe]travail\s*partiel|t[éèe]l[éèe]travail\s*\d\s*j|remote\s*partiel|t[éèe]l[éèe]travail\s*possible|t[éèe]l[éèe]travail\s*ponctuel)\b", re.I), "Hybride / Télétravail partiel"),
    (re.compile(r"\b(sur\s*site|onsite|on-site|pr[éèe]sentiel)\b", re.I), "Présentiel"),
]

SALARY_RE = re.compile(
    r"(?:"
    r"(?:\d{2}[\s\u202f.]?\d{3}|\d{2,3}\s*k)\s*(?:€|EUR)?\s*(?:à|-|–|to)\s*(?:\d{2}[\s\u202f.]?\d{3}|\d{2,3}\s*k)\s*(?:€|EUR)(?:\s*/\s*(?:an|mois|jour|heure)|(?:\s*brut(?:\s*annuel)?))?"
    r"|"
    r"(?:\d{2}[\s\u202f.]?\d{3}|\d{2,3}\s*k)\s*(?:€|EUR)\s*(?:/\s*(?:an|mois|jour|heure)|brut(?:\s*annuel)?)"
    r"|"
    r"(?:USD|EUR|GBP|CHF|\$|€|£)\s*\d{2,3}[,.]?\d{0,3}\s*(?:k|K)?\s*(?:-\s*(?:USD|EUR|GBP|CHF|\$|€|£)?\s*\d{2,3}[,.]?\d{0,3}\s*(?:k|K)?)?"
    r")",
    re.IGNORECASE,
)

EXPERIENCE_RE = re.compile(
    r"(?:"
    r"(?:minimum\s+de\s+|au\s+moins\s+|justifi(?:ez|ant)\s+d['’]?\s*(?:une\s+)?exp[éèe]rience\s+de\s+|exp[éèe]rience\s+(?:de\s+|minimum\s+|requise\s*:?\s*)?)"
    r"(\d+\s*(?:à|-|ou)\s*\d+|\d+)\s*(?:\+\s*)?(?:ans?|années?)"
    r"[^\n.;]{0,90}"
    r"|"
    r"\b(\d+\s*(?:à|-)\s*\d+|\d+\+?)\s*(?:ans?|années?|years?)\s+(?:d['’]exp[éèe]rience|of\s+experience)[^\n.;]{0,90}"
    r"|"
    r"exp[éèe]rience\s+dans\s+(?:le\s+secteur|le\s+domaine|l['’]industrie)[^\n.;]{0,90}"
    r")",
    re.IGNORECASE,
)


def _clean_cell(value: Any) -> str:
    """Normalize text for clean single-cell CSV/Google Sheets representation."""
    if value is None:
        return ""
    if isinstance(value, list):
        items = [str(v).strip() for v in value if str(v).strip()]
        return " ; ".join(items)
    text = str(value).strip()
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t\u00a0\u202f]+", " ", text)
    # Collapse multi-line bullet lists into ' ; ' separated items for clean spreadsheet cells
    lines = [re.sub(r"^[-•*–]\s*", "", ln.strip()) for ln in text.splitlines() if ln.strip()]
    return " ; ".join(lines)


def _extract_section_bullets(text: str, heading_patterns: list[str], stop_patterns: list[str], max_items: int = 6) -> list[str]:
    """Extract bullet lines or sentences under a matching section heading."""
    heading_re = re.compile(
        r"(?:^|\n)\s*(?:#+\s*)?(?:" + "|".join(heading_patterns) + r")\s*:?\s*(?:\n|$)",
        re.IGNORECASE,
    )
    stop_re = re.compile(
        r"(?:^|\n)\s*(?:#+\s*)?(?:" + "|".join(stop_patterns) + r")\s*:?\s*(?:\n|$)",
        re.IGNORECASE,
    )
    match = heading_re.search(text)
    if not match:
        return []
    start = match.end()
    stop_match = stop_re.search(text, start)
    block = text[start:stop_match.start()] if stop_match else text[start:start + 1800]
    items: list[str] = []
    for raw_line in block.splitlines():
        line = re.sub(r"^[-•*–]\s*", "", raw_line.strip())
        if not line or len(line) < 4:
            continue
        if len(line) > 220:
            line = line[:217].rstrip() + "..."
        items.append(line)
        if len(items) >= max_items:
            break
    return items


def extract_matrix_from_text(
    raw_text: str,
    *,
    title: str = "",
    company: str = "",
    location: str = "",
    url: str = "",
    portal: str = "",
    salary: str = "",
    score_fit: str = "",
) -> dict[str, str]:
    """Extract the 8 matrix fields deterministically from a job posting's text."""
    cleaned_text, _ = guard(raw_text or "", "auto")

    # 1. Location & Remote policy
    remote_label = ""
    for pat, label in REMOTE_PATTERNS:
        if pat.search(cleaned_text) or pat.search(location or ""):
            remote_label = label
            break
    loc_clean = _clean_cell(location)
    if loc_clean and remote_label and remote_label.lower() not in loc_clean.lower():
        localisation_teletravail = f"{loc_clean} ({remote_label})"
    elif loc_clean:
        localisation_teletravail = loc_clean
    elif remote_label:
        localisation_teletravail = remote_label
    else:
        localisation_teletravail = "Non précisé"

    all_headings = [
        r"t[âa]ches\s+de\s+base",
        r"vos\s+missions",
        r"les\s+missions(?:\s+du\s+poste)?",
        r"missions(?:\s+principales)?",
        r"responsabilit[éèe]s",
        r"what\s+you['’]?ll\s+do",
        r"key\s+responsibilities",
        r"role\s+description",
        r"comp[éèe]tences(?:\s+attendues|\s+requises|\s+techniques)?",
        r"profil(?:\s+recherch[éèe]|\s+de\s+candidat\s+recherch[éèe])?",
        r"votre\s+profil",
        r"qualifications",
        r"requirements",
        r"what\s+we['’]?re\s+looking\s+for",
        r"technologies(?:\s+\w+)?",
        r"outils(?:\s+et\s+technologies)?",
        r"stack\s+technique",
        r"environnement\s+technique",
        r"les\s+avantages",
        r"avantages",
        r"les\s+[éèe]tapes\s+de\s+recrutement",
        r"employeur\s+inclusif",
    ]

    # 4. Missions principales
    mission_headings = [
        r"t[âa]ches\s+de\s+base",
        r"vos\s+missions",
        r"les\s+missions(?:\s+du\s+poste)?",
        r"missions(?:\s+principales)?",
        r"responsabilit[éèe]s",
        r"what\s+you['’]?ll\s+do",
        r"key\s+responsibilities",
    ]
    missions = _extract_section_bullets(cleaned_text, mission_headings, all_headings, max_items=6)
    if not missions:
        # Fallback: look for "Résumé :" or first substantive bullet points
        resume_match = re.search(r"R[éèe]sum[éèe]\s*:\s*([^\n]+)", cleaned_text, re.I)
        if resume_match:
            missions = [resume_match.group(1).strip()]
        else:
            bullets = [
                re.sub(r"^[-•*–]\s*", "", ln.strip())
                for ln in cleaned_text.splitlines()
                if ln.strip().startswith(("-", "•", "*")) and len(ln.strip()) > 20
            ]
            missions = bullets[:4]

    # 5. Compétences attendues
    skill_headings = [
        r"comp[éèe]tences(?:\s+attendues|\s+requises|\s+techniques)?",
        r"votre\s+profil",
        r"profil(?:\s+recherch[éèe]|\s+de\s+candidat\s+recherch[éèe])?",
        r"qualifications",
        r"requirements",
        r"what\s+we['’]?re\s+looking\s+for",
    ]
    skills = _extract_section_bullets(cleaned_text, skill_headings, all_headings, max_items=6)
    if not skills:
        noter = _extract_section_bullets(cleaned_text, [r"[àa]\s+noter\s+sur\s+ce\s+job"], all_headings, max_items=5)
        skills = [s for s in noter if "cliquez dessus" not in s.lower()]

    # 6. Outils et technologies
    tech_headings = [
        r"technologies(?:\s+\w+)?",
        r"outils(?:\s+et\s+technologies)?",
        r"stack\s+technique",
        r"environnement\s+technique",
    ]
    tech_section = _extract_section_bullets(cleaned_text, tech_headings, all_headings, max_items=6)
    detected_tools: list[str] = []
    seen_tools: set[str] = set()
    for m in KNOWN_TOOLS_RE.finditer(cleaned_text):
        tok = re.sub(r"\s+", " ", m.group(1).strip())
        key = tok.lower()
        if key not in seen_tools:
            seen_tools.add(key)
            detected_tools.append(tok)
    if tech_section and detected_tools:
        outils_str = " ; ".join(tech_section) + f" (Outils détectés : {', '.join(detected_tools)})"
    elif detected_tools:
        outils_str = ", ".join(detected_tools)
    elif tech_section:
        outils_str = " ; ".join(tech_section)
    else:
        outils_str = "Non spécifié"

    # 7. Expérience sectorielle demandée
    exp_matches: list[str] = []
    for m in EXPERIENCE_RE.finditer(cleaned_text):
        snippet = _clean_cell(m.group(0))
        if snippet and snippet not in exp_matches:
            exp_matches.append(snippet)
    for ln in cleaned_text.splitlines():
        if re.search(r"\b(secteur|domaine|industrie|bac\s*\+\s*\d|exp[éèe]rience)\b", ln, re.I):
            clean_ln = re.sub(r"^[-•*–]\s*", "", ln.strip())
            if 10 <= len(clean_ln) <= 140 and clean_ln not in exp_matches:
                exp_matches.append(clean_ln)
        if len(exp_matches) >= 3:
            break
    experience_str = " ; ".join(exp_matches[:3]) if exp_matches else "Non précisé"

    # 8. Salaire
    salaire_str = _clean_cell(salary)
    if not salaire_str:
        sal_m = SALARY_RE.search(cleaned_text)
        if sal_m:
            salaire_str = _clean_cell(sal_m.group(0))
        else:
            salaire_str = "Non communiqué"

    return {
        "intitule_offre": _clean_cell(title) or "Sans titre",
        "entreprise": _clean_cell(company) or "Non précisée",
        "localisation_teletravail": localisation_teletravail,
        "missions_principales": _clean_cell(missions) or "Voir descriptif de l'offre",
        "competences_attendues": _clean_cell(skills) or "Voir descriptif de l'offre",
        "outils_technologies": _clean_cell(outils_str),
        "experience_sectorielle": _clean_cell(experience_str),
        "salaire": salaire_str,
        "score_fit": _clean_cell(score_fit),
        "portail": _clean_cell(portal) or "Web",
        "date_extraction": date.today().isoformat(),
        "url": _clean_cell(url),
    }


def normalize_row(item: dict[str, Any]) -> dict[str, str]:
    """Normalize an input job object (already extracted or raw) into the 12-column matrix schema."""
    has_matrix_keys = any(
        k in item
        for k in (
            "intitule_offre",
            "missions_principales",
            "competences_attendues",
            "outils_technologies",
            "experience_sectorielle",
        )
    )
    if not has_matrix_keys and item.get("description"):
        return extract_matrix_from_text(
            str(item.get("description", "")),
            title=str(item.get("title") or item.get("intitule_offre") or ""),
            company=str(item.get("company") or item.get("entreprise") or ""),
            location=str(item.get("location") or item.get("localisation_teletravail") or ""),
            url=str(item.get("url") or ""),
            portal=str(item.get("portal") or item.get("portail") or ""),
            salary=str(item.get("salary") or item.get("salaire") or ""),
            score_fit=str(item.get("score") or item.get("fit") or item.get("score_fit") or ""),
        )

    return {
        "intitule_offre": _clean_cell(item.get("intitule_offre") or item.get("title") or "Sans titre"),
        "entreprise": _clean_cell(item.get("entreprise") or item.get("company") or "Non précisée"),
        "localisation_teletravail": _clean_cell(
            item.get("localisation_teletravail") or item.get("location") or "Non précisé"
        ),
        "missions_principales": _clean_cell(
            item.get("missions_principales") or item.get("strengths") or "Non renseigné"
        ),
        "competences_attendues": _clean_cell(
            item.get("competences_attendues") or item.get("skills") or "Non renseigné"
        ),
        "outils_technologies": _clean_cell(
            item.get("outils_technologies") or item.get("tools") or "Non spécifié"
        ),
        "experience_sectorielle": _clean_cell(
            item.get("experience_sectorielle") or item.get("experience") or "Non précisé"
        ),
        "salaire": _clean_cell(item.get("salaire") or item.get("salary") or "Non communiqué"),
        "score_fit": _clean_cell(
            item.get("score_fit") or item.get("score") or item.get("fit") or ""
        ),
        "portail": _clean_cell(item.get("portail") or item.get("portal") or "Web"),
        "date_extraction": _clean_cell(
            item.get("date_extraction") or item.get("first_seen") or item.get("date") or date.today().isoformat()
        ),
        "url": _clean_cell(item.get("url") or ""),
    }


def export_matrix(
    rows: list[dict[str, str]],
    csv_path: Path = DEFAULT_CSV,
    json_path: Path = DEFAULT_JSON,
    *,
    append: bool = True,
    delimiter: str = ",",
) -> dict[str, Any]:
    """Export normalized matrix rows to UTF-8-SIG CSV and JSON, deduplicating by URL or (entreprise, intitule)."""
    existing: list[dict[str, str]] = []
    if append and json_path.is_file():
        try:
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("offers"), list):
                existing = loaded["offers"]
            elif isinstance(loaded, list):
                existing = loaded
        except (OSError, json.JSONDecodeError):
            existing = []

    merged: list[dict[str, str]] = []
    seen_keys: dict[str, int] = {}

    def _row_key(r: dict[str, str]) -> str:
        url = (r.get("url") or "").strip().rstrip("/").lower()
        if url:
            return f"url:{url}"
        return f"pair:{(r.get('entreprise') or '').lower().strip()}|{(r.get('intitule_offre') or '').lower().strip()}"

    for r in existing:
        norm_r = normalize_row(r)
        k = _row_key(norm_r)
        seen_keys[k] = len(merged)
        merged.append(norm_r)

    added = 0
    updated = 0
    for r in rows:
        norm_r = normalize_row(r)
        k = _row_key(norm_r)
        if k in seen_keys:
            idx = seen_keys[k]
            merged[idx] = norm_r
            updated += 1
        else:
            seen_keys[k] = len(merged)
            merged.append(norm_r)
            added += 1

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV with UTF-8 BOM (utf-8-sig) so Google Sheets and Excel on macOS open French accents cleanly
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([label for _, label in MATRIX_COLUMNS])
        for row in merged:
            writer.writerow([row.get(key, "") for key, _ in MATRIX_COLUMNS])

    # Write structured JSON
    json_payload = {
        "updated_at": date.today().isoformat(),
        "total_offers": len(merged),
        "columns": [{"key": k, "label": label} for k, label in MATRIX_COLUMNS],
        "offers": merged,
    }
    json_path.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "added": added,
        "updated": updated,
        "total": len(merged),
    }


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    ext = sub.add_parser("extract", help="Extract the 8 matrix fields from a job posting text or JSON")
    ext.add_argument("--in", dest="infile", type=Path, default=None, help="Input file (text or JSON; default: stdin)")
    ext.add_argument("--title", default="")
    ext.add_argument("--company", default="")
    ext.add_argument("--location", default="")
    ext.add_argument("--url", default="")
    ext.add_argument("--portal", default="")
    ext.add_argument("--salary", default="")
    ext.add_argument("--score-fit", default="")
    ext.add_argument("--export", action="store_true", help="Also append directly to CSV and JSON exports")

    exp = sub.add_parser("export", help="Export a JSON list/object of job offers to CSV and JSON")
    exp.add_argument("--in", dest="infile", type=Path, required=True, help="JSON file containing job offers")
    exp.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    exp.add_argument("--json", type=Path, default=DEFAULT_JSON)
    exp.add_argument("--overwrite", action="store_true", help="Replace existing export instead of merging")
    exp.add_argument("--delimiter", default=",", help="CSV delimiter (default ',' for Google Sheets)")

    fseen = sub.add_parser("from-seen", help="Export entries from job_scraper/seen_jobs.json into the matrix CSV/JSON")
    fseen.add_argument("--state", type=Path, default=SEEN_JOBS)
    fseen.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    fseen.add_argument("--json", type=Path, default=DEFAULT_JSON)

    args = parser.parse_args(argv)

    if args.command == "extract":
        raw = args.infile.read_text(encoding="utf-8", errors="replace") if args.infile else sys.stdin.read()
        # Check if raw is JSON from a portal CLI `detail --format json`
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                row = extract_matrix_from_text(
                    str(parsed.get("description") or ""),
                    title=args.title or str(parsed.get("title") or ""),
                    company=args.company or str(parsed.get("company") or ""),
                    location=args.location or str(parsed.get("location") or ""),
                    url=args.url or str(parsed.get("url") or ""),
                    portal=args.portal or str(parsed.get("portal") or ""),
                    salary=args.salary or str(parsed.get("salary") or ""),
                    score_fit=args.score_fit or str(parsed.get("score_fit") or ""),
                )
            else:
                row = extract_matrix_from_text(
                    raw,
                    title=args.title,
                    company=args.company,
                    location=args.location,
                    url=args.url,
                    portal=args.portal,
                    salary=args.salary,
                    score_fit=args.score_fit,
                )
        except json.JSONDecodeError:
            row = extract_matrix_from_text(
                raw,
                title=args.title,
                company=args.company,
                location=args.location,
                url=args.url,
                portal=args.portal,
                salary=args.salary,
                score_fit=args.score_fit,
            )
        if args.export:
            summary = export_matrix([row])
            print(json.dumps({"offer": row, "export": summary}, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(row, indent=2, ensure_ascii=False))
        return 0

    if args.command == "export":
        data = json.loads(args.infile.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            items = data.get("offers") or data.get("results") or [data]
        elif isinstance(data, list):
            items = data
        else:
            print("extract_job_matrix: input JSON must be an object or array", file=sys.stderr)
            return 1
        summary = export_matrix(
            items,
            csv_path=args.csv,
            json_path=args.json,
            append=not args.overwrite,
            delimiter=args.delimiter,
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    if args.command == "from-seen":
        if not args.state.is_file():
            print(f"extract_job_matrix: {args.state} not found", file=sys.stderr)
            return 1
        doc = json.loads(args.state.read_text(encoding="utf-8"))
        seen_map = doc.get("seen", doc) if isinstance(doc, dict) else {}
        items = [v for v in seen_map.values() if isinstance(v, dict)]
        summary = export_matrix(items, csv_path=args.csv, json_path=args.json, append=True)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
