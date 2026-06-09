#!/usr/bin/env python3
"""Validate all SKILL.md files in the skills/ directory.

Checks:
- Frontmatter starts with --- and has valid YAML
- Required fields: name, description
- Description length ≤ 1024 chars
- Name ≤ 64 chars, lowercase + hyphens
- Total file content ≤ 100,000 chars
- Non-empty body after frontmatter

Usage:
    python scripts/validate-skills.py [--fix]
"""

import re
import sys
import yaml
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

REQUIRED_FIELDS = ["name", "description"]
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_CONTENT_CHARS = 100_000


def validate_skill(skill_path: Path, fix: bool = False) -> list[str]:
    errors = []
    content = skill_path.read_text(encoding="utf-8")

    # Check total length
    if len(content) > MAX_CONTENT_CHARS:
        errors.append(f"  Total content {len(content)} chars > {MAX_CONTENT_CHARS}")

    # Check starts with ---
    if not content.startswith("---"):
        errors.append("  Does NOT start with '---'")
        return errors

    # Find closing ---
    m = re.search(r"\n---\s*\n", content[3:])
    if not m:
        errors.append("  No closing '---' found after frontmatter")
        return errors

    frontmatter_str = content[3 : m.start() + 3]
    body = content[m.start() + 7 :].strip()

    # Parse YAML
    try:
        fm = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError as e:
        errors.append(f"  Invalid YAML frontmatter: {e}")
        return errors

    if not isinstance(fm, dict):
        errors.append("  Frontmatter is not a YAML mapping")
        return errors

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in fm or not fm[field]:
            errors.append(f"  Missing or empty required field: '{field}'")

    # Name validation
    name = fm.get("name", "")
    if name and len(name) > MAX_NAME_LENGTH:
        errors.append(f"  Name '{name}' length {len(name)} > {MAX_NAME_LENGTH}")
    if name and not re.match(r"^[a-z0-9][a-z0-9_-]*$", name):
        errors.append(f"  Name '{name}' should be lowercase with hyphens/underscores")

    # Description validation
    desc = fm.get("description", "")
    if desc and len(desc) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"  Description length {len(desc)} > {MAX_DESCRIPTION_LENGTH}")

    # Check non-empty body
    if not body:
        errors.append("  Empty body after frontmatter")

    return errors


def main():
    fix = "--fix" in sys.argv
    all_skills = sorted(SKILLS_DIR.rglob("SKILL.md"))
    total_errors = 0
    total_warnings = 0

    print(f"Found {len(all_skills)} SKILL.md files to validate\n")

    for skill_path in all_skills:
        rel_path = skill_path.relative_to(SKILLS_DIR.parent)
        errors = validate_skill(skill_path, fix=fix)
        if errors:
            total_errors += len(errors)
            print(f"❌ {rel_path}")
            for err in errors:
                print(f"   {err}")
        else:
            print(f"✅ {rel_path}")

    print(f"\n{'='*50}")
    print(f"Total skills: {len(all_skills)}")
    print(f"Errors: {total_errors}")
    print(f"{'='*50}")

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
