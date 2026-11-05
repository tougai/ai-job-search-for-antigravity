#!/usr/bin/env python3
"""Supply-chain and privacy guards for the Antigravity workspace.

Run from anywhere: python tools/security_guards.py

Checks:
1. .gitignore — all personal-data ignore rules must be present, and no
   un-allowlisted negation (!pattern) may re-include them.
2. .agents/**/package.json — no npm/bun lifecycle scripts (preinstall,
   install, postinstall, prepare, prepack), no trustedDependencies, no
   workspaces, and no bunfig.toml or .npmrc beside the manifest.
3. No tracked node_modules in git.
4. .agents/skills/*/SKILL.md and .agents/commands/*.md — valid UTF-8, no
   frontmatter `hooks`, and no !`command` dynamic-context lines.
5. No leftover .claude/ directory or CLAUDE.md file.

Stdlib only. Exit 0 on success, 1 with a failure list otherwise.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []

REQUIRED_IGNORE_RULES = [
    "salary_data.json",
    "**/job_scraper/seen_jobs.json",
    "**/job_scraper/notion_sync.json",
    "**/job_scraper/job_matrix_export.csv",
    "**/job_scraper/job_matrix_export.json",
    "**/job_scraper/*.md",
    "*_BehavioralReport.pdf",
    "linkedin_Profile.pdf",
    "cv/main_*.*",
    "!cv/main_example.tex",
    "cv/*.txt",
    "cover_letters/cover_*.*",
    "cover_letters/Cover_*.*",
    "documents/cv/**",
    "documents/linkedin/**",
    "documents/diplomas/**",
    "documents/references/**",
    "documents/projects/**",
    "documents/applications/**",
    "documents/postings/**",
    "documents/interview/**",
    "job_search_tracker.csv",
    "gmail_sync/",
    "reports/",
    "upskill/*.md",
    "**/upskill/report-*.md",
    ".env",
    ".env.*",
    "company_research/*.json",
]

ALLOWED_IGNORE_NEGATIONS = {
    "!cover_letters/OpenFonts/fonts/**",
    "!cv/main_example.tex",
    "!cover_letters/cover_example.tex",
    "!documents/**/.gitkeep",
}

FORBIDDEN_SCRIPTS = {"preinstall", "install", "postinstall", "prepare", "prepack"}
FORBIDDEN_MANIFEST_KEYS = {"trustedDependencies", "workspaces"}
INSTALL_CONFIG_FILES = ("bunfig.toml", ".npmrc")
DYNAMIC_CONTEXT = re.compile(r"!`[^`\n]+`")
_FRONTMATTER_KEY = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")


def _key(name: str) -> str:
    return name.lower().replace("-", "").replace("_", "")


def _frontmatter(text: str):
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None
    data: dict = {}
    key = None
    for raw in lines[1:end]:
        if raw[:1] in (" ", "\t"):
            if key is None:
                continue
            stripped = raw.strip()
            if stripped.startswith("- "):
                if not isinstance(data[key], list):
                    data[key] = []
                data[key].append(stripped[2:].strip())
            elif isinstance(data[key], str):
                data[key] = (data[key] + " " + stripped).strip()
            continue
        match = _FRONTMATTER_KEY.match(raw)
        if not match:
            key = None
            continue
        key, value = match.group(1), match.group(2).strip()
        data[key] = "" if value in (">", "|", ">-", "|-") else value
    return data


def _gitignore_lines(path: Path) -> set[str]:
    lines = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip("\r\n")
        if not line or line.startswith("#"):
            continue
        lines.add(line)
    return lines


def check_gitignore() -> None:
    path = ROOT / ".gitignore"
    if not path.is_file():
        errors.append(".gitignore: missing")
        return
    present = _gitignore_lines(path)
    for rule in REQUIRED_IGNORE_RULES:
        if rule not in present:
            errors.append(f".gitignore: required personal-data rule missing: {rule!r}")
    for line in sorted(present):
        if line.startswith("!") and line not in ALLOWED_IGNORE_NEGATIONS:
            errors.append(f".gitignore: un-allowlisted negation rule: {line!r}")


def check_package_manifests() -> None:
    for manifest in sorted((ROOT / ".agents").rglob("package.json")):
        if "node_modules" in manifest.parts:
            continue
        rel = manifest.relative_to(ROOT).as_posix()
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{rel}: unreadable or invalid JSON: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{rel}: manifest must be a JSON object")
            continue
        scripts = data.get("scripts", {})
        if isinstance(scripts, dict):
            for bad in sorted(FORBIDDEN_SCRIPTS & set(scripts)):
                errors.append(f"{rel}: forbidden lifecycle script {bad!r}")
        for bad_key in sorted(FORBIDDEN_MANIFEST_KEYS & set(data)):
            errors.append(f"{rel}: forbidden manifest key {bad_key!r}")
        for cfg in INSTALL_CONFIG_FILES:
            if (manifest.parent / cfg).exists():
                errors.append(f"{rel}: forbidden install config file {cfg!r}")


def check_tracked_node_modules() -> None:
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=False
        )
    except OSError:
        return
    if proc.returncode != 0:
        return
    for rel in proc.stdout.decode("utf-8", errors="replace").split("\x00"):
        if rel and "node_modules" in rel.split("/"):
            errors.append(f"tracked path inside node_modules: {rel!r}")


def check_skills_and_commands() -> None:
    skills = sorted(ROOT.glob(".agents/skills/*/SKILL.md"))
    commands = sorted((ROOT / ".agents" / "commands").glob("*.md"))
    for path in skills + commands:
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{rel}: unreadable (must be UTF-8): {exc}")
            continue
        for match in DYNAMIC_CONTEXT.finditer(text):
            errors.append(f"{rel}: dynamic-context line {match.group(0)!r} is forbidden")
        data = _frontmatter(text)
        if data is not None and "hooks" in {_key(k) for k in data}:
            errors.append(f"{rel}: frontmatter `hooks` is forbidden")
        if data is None and path in skills:
            errors.append(f"{rel}: missing or unterminated frontmatter (expected --- ... ---)")


def check_no_legacy_claude_files() -> None:
    if (ROOT / ".claude").exists():
        errors.append(".claude/ directory still exists; all files must live under .agents/")
    if (ROOT / "CLAUDE.md").exists():
        errors.append("CLAUDE.md still exists; candidate profile must live in GEMINI.md")


def main() -> int:
    check_gitignore()
    check_package_manifests()
    check_tracked_node_modules()
    check_skills_and_commands()
    check_no_legacy_claude_files()
    if errors:
        print(f"security_guards: {len(errors)} failure(s)")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(
        "security_guards: OK (gitignore rules, package manifests, no tracked node_modules, "
        "Antigravity skills/commands, no legacy .claude files)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
