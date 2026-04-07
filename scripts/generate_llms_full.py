"""Generate docs/llms-full.txt by concatenating documentation Markdown files."""
from __future__ import annotations

import pathlib

# Ordered list of doc files to include
DOC_FILES: list[str] = [
    "index.md",
    "quickstart.md",
    "connection.md",
    "dialect-features.md",
    "types.md",
    "reflection.md",
    "ddl.md",
    "limitations.md",
    "api-reference.md",
    "development.md",
]


def main() -> None:
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    docs_dir = repo_root / "docs"
    output = docs_dir / "llms-full.txt"

    sections: list[str] = []
    for filename in DOC_FILES:
        filepath = docs_dir / filename
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8").strip()
            sections.append(content)

    output.write_text("\n\n---\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Generated {output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
