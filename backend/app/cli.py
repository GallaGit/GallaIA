"""Tiny AgentOS YAML CLI (Phase 6 slice 1).

Usage (from backend/):
  python -m app.cli export [-o agentos.yml] [--project-slug default]
  python -m app.cli import [-i agentos.yml] [--project-slug default]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="GallaIA agentos.yml export/import (Phase 6 slice 1)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    exp = sub.add_parser("export", help="Export agents+templates to agentos.yml")
    exp.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("agentos.yml"),
        help="Output path (default: ./agentos.yml)",
    )
    exp.add_argument(
        "--project-slug",
        default="default",
        help="Project slug to export (default: default)",
    )
    exp.add_argument(
        "--stdout",
        action="store_true",
        help="Print YAML to stdout instead of writing a file",
    )

    imp = sub.add_parser("import", help="Import/apply agentos.yml (idempotent upsert)")
    imp.add_argument(
        "-i",
        "--file",
        type=Path,
        default=Path("agentos.yml"),
        help="Input path (default: ./agentos.yml)",
    )
    imp.add_argument(
        "--project-slug",
        default="default",
        help="Target project slug (default: default)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    # Ensure backend cwd packages resolve when invoked as python -m app.cli
    parser = _build_parser()
    args = parser.parse_args(argv)

    from app.db.init_db import init_db
    from app.db.session import SessionLocal
    from app.services.agentos_yml import (
        dump_agentos_yml,
        export_agentos_yml,
        import_agentos_yml,
        load_agentos_yml,
        write_agentos_yml,
    )

    init_db()
    db = SessionLocal()
    try:
        if args.command == "export":
            doc = export_agentos_yml(db, project_slug=args.project_slug)
            if args.stdout:
                sys.stdout.write(dump_agentos_yml(doc))
            else:
                write_agentos_yml(args.out, doc)
                print(f"Exported {len(doc.agents)} agents, {len(doc.templates)} templates -> {args.out}")
            return 0

        if args.command == "import":
            if not args.file.is_file():
                print(f"File not found: {args.file}", file=sys.stderr)
                return 1
            doc = load_agentos_yml(args.file)
            result = import_agentos_yml(db, doc, project_slug=args.project_slug)
            print(
                "Import OK: "
                f"agents +{result.agents_created}/~{result.agents_updated}, "
                f"templates +{result.templates_created}/~{result.templates_updated}"
            )
            return 0

        parser.error(f"Unknown command: {args.command}")
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
