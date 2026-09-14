"""Tiny AgentOS YAML / CLI (Phase 6).

Usage (from backend/):
  python -m app.cli export|pull [-o agentos.yml] [--project-slug default]
  python -m app.cli import|push [-i agentos.yml] [--project-slug default]
  python -m app.cli create-agent --name NAME --role ROLE [options]
  python -m app.cli update-agent --name NAME [options]
  python -m app.cli create-template --slug SLUG --name NAME [--from-yaml FILE]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="GallaIA agentos.yml + agent create/update CLI (Phase 6)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for cmd, help_text in (
        ("export", "Export agents+templates to agentos.yml"),
        ("pull", "Alias for export (YAML ← control plane)"),
    ):
        exp = sub.add_parser(cmd, help=help_text)
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

    for cmd, help_text in (
        ("import", "Import/apply agentos.yml (idempotent upsert)"),
        ("push", "Alias for import (YAML → control plane)"),
    ):
        imp = sub.add_parser(cmd, help=help_text)
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

    create = sub.add_parser(
        "create-agent",
        help="Create an agent (same row shape as UI/API / YAML import)",
    )
    create.add_argument("--name", help="Agent name (idempotent key)")
    create.add_argument(
        "--role",
        default=None,
        help="Role prompt text (maps to role_prompt)",
    )
    create.add_argument("--title", default=None, help="Display title (default: name)")
    create.add_argument("--model", default="claude-sonnet-4")
    create.add_argument("--foundational-prompt", default="", dest="foundational_prompt")
    create.add_argument(
        "--runner-preference",
        default="mock",
        dest="runner_preference",
        choices=["mock", "cloud", "local"],
    )
    create.add_argument(
        "--from-yaml",
        type=Path,
        default=None,
        dest="from_yaml",
        help="YAML snippet (bare agent or agents: [...]) instead of flags",
    )
    create.add_argument("--project-slug", default="default")

    update = sub.add_parser(
        "update-agent",
        help="Update agent fields by name (partial)",
    )
    update.add_argument("--name", required=True, help="Existing agent name")
    update.add_argument("--role", default=None, help="New role_prompt")
    update.add_argument("--title", default=None)
    update.add_argument("--model", default=None)
    update.add_argument(
        "--foundational-prompt",
        default=None,
        dest="foundational_prompt",
    )
    update.add_argument(
        "--runner-preference",
        default=None,
        dest="runner_preference",
        choices=["mock", "cloud", "local"],
    )
    update.add_argument("--project-slug", default="default")

    tmpl = sub.add_parser(
        "create-template",
        help="Create one template (lean; prefer import for bulk)",
    )
    tmpl.add_argument("--slug", default=None)
    tmpl.add_argument("--name", default=None)
    tmpl.add_argument("--description", default=None)
    tmpl.add_argument(
        "--from-yaml",
        type=Path,
        default=None,
        dest="from_yaml",
        help="YAML snippet (bare template or templates: [...])",
    )
    tmpl.add_argument("--project-slug", default="default")

    return parser


def _cmd_export(args) -> int:
    from app.services.agentos_yml import (
        dump_agentos_yml,
        export_agentos_yml,
        write_agentos_yml,
    )

    doc = export_agentos_yml(args.db, project_slug=args.project_slug)
    if args.stdout:
        sys.stdout.write(dump_agentos_yml(doc))
    else:
        write_agentos_yml(args.out, doc)
        print(
            f"Exported {len(doc.agents)} agents, {len(doc.templates)} templates -> {args.out}"
        )
    return 0


def _cmd_import(args) -> int:
    from app.services.agentos_yml import import_agentos_yml, load_agentos_yml

    if not args.file.is_file():
        print(f"File not found: {args.file}", file=sys.stderr)
        return 1
    doc = load_agentos_yml(args.file)
    result = import_agentos_yml(args.db, doc, project_slug=args.project_slug)
    print(
        "Import OK: "
        f"agents +{result.agents_created}/~{result.agents_updated}, "
        f"templates +{result.templates_created}/~{result.templates_updated}"
    )
    return 0


def _cmd_create_agent(args) -> int:
    from app.services.agentos_yml import (
        create_agent,
        create_agent_from_yml,
        parse_agent_yml_snippet,
    )

    if args.from_yaml is not None:
        if not args.from_yaml.is_file():
            print(f"File not found: {args.from_yaml}", file=sys.stderr)
            return 1
        entry = parse_agent_yml_snippet(args.from_yaml.read_text(encoding="utf-8"))
        agent = create_agent_from_yml(
            args.db, entry, project_slug=args.project_slug
        )
    else:
        if not args.name:
            print("create-agent requires --name or --from-yaml", file=sys.stderr)
            return 1
        if args.role is None:
            print("create-agent requires --role (or --from-yaml)", file=sys.stderr)
            return 1
        agent = create_agent(
            args.db,
            name=args.name,
            title=args.title,
            role_prompt=args.role,
            model=args.model,
            foundational_prompt=args.foundational_prompt,
            runner_preference=args.runner_preference,
            project_slug=args.project_slug,
        )
    print(
        f"Created agent id={agent.id} name={agent.name!r} title={agent.title!r}"
    )
    return 0


def _cmd_update_agent(args) -> int:
    from app.services.agentos_yml import update_agent

    if all(
        v is None
        for v in (
            args.role,
            args.title,
            args.model,
            args.foundational_prompt,
            args.runner_preference,
        )
    ):
        print(
            "update-agent: pass at least one field "
            "(--role/--title/--model/--foundational-prompt/--runner-preference)",
            file=sys.stderr,
        )
        return 1

    agent = update_agent(
        args.db,
        name=args.name,
        title=args.title,
        role_prompt=args.role,
        model=args.model,
        foundational_prompt=args.foundational_prompt,
        runner_preference=args.runner_preference,
        project_slug=args.project_slug,
    )
    print(
        f"Updated agent id={agent.id} name={agent.name!r} title={agent.title!r}"
    )
    return 0


def _cmd_create_template(args) -> int:
    from app.schemas.agentos_yml import TemplateYml
    from app.services.agentos_yml import create_template, parse_template_yml_snippet

    if args.from_yaml is not None:
        if not args.from_yaml.is_file():
            print(f"File not found: {args.from_yaml}", file=sys.stderr)
            return 1
        entry = parse_template_yml_snippet(
            args.from_yaml.read_text(encoding="utf-8")
        )
    else:
        if not args.slug or not args.name:
            print(
                "create-template requires --slug and --name (or --from-yaml)",
                file=sys.stderr,
            )
            return 1
        entry = TemplateYml(
            slug=args.slug,
            name=args.name,
            description=args.description,
            steps=[],
        )

    template = create_template(args.db, entry, project_slug=args.project_slug)
    print(
        f"Created template id={template.id} slug={template.slug!r} "
        f"name={template.name!r} steps={len(entry.steps)}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    from app.db.init_db import init_db
    from app.db.session import SessionLocal
    from app.exceptions import AppError

    init_db()
    db = SessionLocal()
    args.db = db
    try:
        try:
            if args.command in ("export", "pull"):
                return _cmd_export(args)
            if args.command in ("import", "push"):
                return _cmd_import(args)
            if args.command == "create-agent":
                return _cmd_create_agent(args)
            if args.command == "update-agent":
                return _cmd_update_agent(args)
            if args.command == "create-template":
                return _cmd_create_template(args)
            parser.error(f"Unknown command: {args.command}")
            return 2
        except AppError as exc:
            print(f"Error: {exc.message}", file=sys.stderr)
            return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
