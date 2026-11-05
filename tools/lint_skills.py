#!/usr/bin/env python3
"""Lint the repo's Antigravity skills, commands, and profile configuration.

Run from anywhere: python tools/lint_skills.py

Checks:
- Every SKILL.md (.agents/skills/*/SKILL.md) has YAML frontmatter that parses,
  with non-empty `name` and `description` keys
- Every .agents/commands/*.md starts with a `# /<name>` title
- GEMINI.md and AGENTS.md exist and are valid UTF-8

Exit code 0 on success, 1 with a failure list otherwise.
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("lint_skills.py requires PyYAML: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def check_skill(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append(f"{rel(path)}: missing YAML frontmatter (file must start with ---)")
        return
    end = text.find("\n---", 4)
    if end == -1:
        errors.append(f"{rel(path)}: unterminated YAML frontmatter")
        return
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        errors.append(f"{rel(path)}: frontmatter is not valid YAML: {exc}")
        return
    if not isinstance(data, dict):
        errors.append(f"{rel(path)}: frontmatter did not parse to a mapping")
        return
    for key in ("name", "description"):
        if not data.get(key):
            errors.append(f"{rel(path)}: frontmatter missing required key '{key}'")


def check_command(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").lstrip().splitlines()
    first = lines[0] if lines else ""
    if not first.startswith("# /"):
        errors.append(f"{rel(path)}: command file must start with a '# /<name>' title (found: {first[:50]!r})")


def check_profile_files() -> None:
    for name in ("GEMINI.md", "AGENTS.md"):
        path = ROOT / name
        if not path.is_file():
            errors.append(f"{name}: missing required root configuration file")


def main() -> int:
    skills = sorted(ROOT.glob(".agents/skills/*/SKILL.md"))
    commands = sorted((ROOT / ".agents" / "commands").glob("*.md"))
    if not skills:
        errors.append("no SKILL.md files found under .agents/skills/")
    if not commands:
        errors.append("no command files found under .agents/commands/")

    for skill in skills:
        check_skill(skill)
    for command in commands:
        check_command(command)
    check_profile_files()

    if errors:
        print(f"lint_skills: {len(errors)} failure(s)")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"lint_skills: OK ({len(skills)} Antigravity skills, {len(commands)} commands, GEMINI.md, AGENTS.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
