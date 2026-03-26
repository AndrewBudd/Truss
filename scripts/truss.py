#!/usr/bin/env python3
"""
Truss — Knowledge engineering framework CLI.

Commands:
    build-deps    Build the reverse dependency index
    detect-stale  Identify documents with out-of-date pinned references
    validate      Validate documents against kind-specific rules
    resolve       Interactive resolution workflow for stale documents
    new           Create a new document with proper frontmatter
    add-remote    Register a remote Truss repository
    list-remotes  List registered remote Truss repositories
    init          Initialize a new Truss project
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import textwrap
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return Path(result.stdout.strip())


def git_file_hash(root: Path, filepath: str) -> Optional[str]:
    """Return the short commit hash of the last commit that touched *filepath*."""
    result = subprocess.run(
        ["git", "-C", str(root), "log", "-1", "--format=%h", "--", filepath],
        capture_output=True, text=True,
    )
    h = result.stdout.strip()
    return h if h else None


def git_diff(root: Path, old_hash: str, filepath: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "diff", f"{old_hash}..HEAD", "--", filepath],
        capture_output=True, text=True,
    )
    return result.stdout


def load_config(root: Path) -> dict:
    """Load .truss/config.yaml as a simple dict (minimal YAML parser)."""
    config_path = root / ".truss" / "config.yaml"
    if not config_path.exists():
        return {}

    config = {}
    text = config_path.read_text(encoding="utf-8")
    current_section = None
    current_dict = {}

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Top-level key with a mapping value (ends with : and no value, or {})
        if not line.startswith(" ") and ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()

            if val == "{}" or val == "":
                # Start of a section or empty dict
                if current_section and current_dict:
                    config[current_section] = current_dict
                    current_dict = {}
                current_section = key
                if val == "{}":
                    config[key] = {}
                    current_section = None
                continue
            else:
                if current_section and current_dict:
                    config[current_section] = current_dict
                    current_dict = {}
                    current_section = None
                config[key] = val.strip('"').strip("'")
                continue

        # Nested key within a section
        if current_section and line.startswith("  ") and ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            current_dict[key] = val

    if current_section:
        if current_dict:
            config[current_section] = current_dict
        elif current_section not in config:
            config[current_section] = {}

    return config


def save_config(root: Path, config: dict):
    """Write config back to .truss/config.yaml."""
    config_path = root / ".truss" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Truss project configuration"]

    # Write version
    if "version" in config:
        lines.append(f'version: "{config["version"]}"')
        lines.append("")

    # Write kinds
    if "kinds" in config:
        lines.append("# Document kind directories")
        lines.append("kinds:")
        for k, v in config["kinds"].items():
            lines.append(f"  {k}: {v}")
        lines.append("")

    # Write generated
    if "generated" in config:
        lines.append("# Generated artifact paths")
        lines.append("generated:")
        for k, v in config["generated"].items():
            lines.append(f"  {k}: {v}")
        lines.append("")

    # Write remotes
    lines.append("# Remote Truss repositories")
    lines.append("# Register with: python3 scripts/truss.py add-remote <name> <url>")
    remotes = config.get("remotes", {})
    if remotes:
        lines.append("remotes:")
        for name, url in remotes.items():
            lines.append(f"  {name}: \"{url}\"")
    else:
        lines.append("remotes: {}")
    lines.append("")

    # Write validation
    if "validation" in config:
        lines.append("# Validation settings")
        lines.append("validation:")
        for k, v in config["validation"].items():
            lines.append(f"  # {k.replace('_', ' ').title()}")
            lines.append(f"  {k}: {v}")
        lines.append("")

    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# External reference detection
# ---------------------------------------------------------------------------

EXTERNAL_URL_RE = re.compile(r"^https?://")
EXTERNAL_SHORTHAND_RE = re.compile(r"^@([^/]+)/(.+)$")


def is_external_ref(ref_str: str) -> bool:
    """Return True if a reference points to an external Truss repository."""
    if EXTERNAL_URL_RE.match(ref_str):
        return True
    if EXTERNAL_SHORTHAND_RE.match(ref_str):
        return True
    return False


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

@dataclass
class Reference:
    ref: str        # e.g. "ground/g-foo.md" or "@other-truss/ground/g-foo.md"
    pin: str = ""   # commit hash
    note: str = ""
    repo: str = ""  # optional repo URL for shorthand external refs


@dataclass
class Document:
    path: str               # relative to repo root
    kind: str = ""
    id: str = ""
    title: str = ""
    created: str = ""
    parameter: str = ""     # generic docs only
    status: str = ""
    assumes: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    raw_frontmatter: str = ""


INTERNAL_REF_RE = re.compile(r"^(ground|hypothetical|generic)/")


def parse_frontmatter(filepath: Path, relpath: str) -> Document:
    """Parse YAML frontmatter from a markdown file into a Document."""
    doc = Document(path=relpath)
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Find frontmatter boundaries
    if not lines or lines[0].strip() != "---":
        return doc

    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return doc

    fm_lines = lines[1:end]
    doc.raw_frontmatter = "\n".join(fm_lines)

    # Simple YAML parser (handles the subset we need)
    current_block = None  # "assumes" or "evidence"
    current_ref = None

    for line in fm_lines:
        stripped = line.strip()

        # Top-level scalar fields
        if not stripped.startswith("-") and ":" in stripped and not stripped.startswith("#"):
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")

            if key == "kind":
                doc.kind = val
            elif key == "id":
                doc.id = val
            elif key == "title":
                doc.title = val
            elif key == "created":
                doc.created = val
            elif key == "parameter":
                doc.parameter = val
            elif key == "status":
                doc.status = val
            elif key == "assumes":
                current_block = "assumes"
                current_ref = None
                continue
            elif key == "evidence":
                current_block = "evidence"
                current_ref = None
                continue
            elif key not in ("ref", "pin", "note", "type", "repo"):
                # Unknown top-level key resets block context
                current_block = None
                current_ref = None
            continue

        # List items within a block
        if current_block and stripped.startswith("-"):
            # Flush previous ref
            if current_ref is not None:
                if current_block == "assumes":
                    doc.assumes.append(current_ref)
                else:
                    doc.evidence.append(current_ref)

            current_ref = Reference(ref="")
            # May have inline key: "- ref: foo"
            inner = stripped.lstrip("-").strip()
            if inner.startswith("ref:"):
                current_ref.ref = inner.partition(":")[2].strip().strip('"').strip("'")
            elif inner.startswith("type:"):
                pass  # evidence type, we track it but don't need it
            continue

        # Continuation keys within a list item
        if current_ref is not None and stripped and not stripped.startswith("-"):
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key == "ref":
                    current_ref.ref = val
                elif key == "pin":
                    current_ref.pin = val
                elif key == "note":
                    current_ref.note = val
                elif key == "repo":
                    current_ref.repo = val

    # Flush last ref
    if current_ref is not None and current_ref.ref:
        if current_block == "assumes":
            doc.assumes.append(current_ref)
        else:
            doc.evidence.append(current_ref)

    return doc


def find_documents(root: Path) -> list[Document]:
    """Find and parse all Truss documents."""
    docs = []
    for kind_dir in ("ground", "hypothetical", "generic"):
        dirpath = root / kind_dir
        if not dirpath.is_dir():
            continue
        for mdfile in sorted(dirpath.glob("*.md")):
            relpath = str(mdfile.relative_to(root))
            doc = parse_frontmatter(mdfile, relpath)
            # Skip non-Truss files (e.g. Jekyll index pages)
            if not doc.kind and mdfile.name == "index.md":
                continue
            docs.append(doc)
    return docs


def internal_refs(doc: Document) -> list[Reference]:
    """Return all references that point to local Truss documents."""
    refs = []
    for r in doc.assumes:
        if INTERNAL_REF_RE.match(r.ref) and not is_external_ref(r.ref):
            refs.append(r)
    for r in doc.evidence:
        if INTERNAL_REF_RE.match(r.ref) and not is_external_ref(r.ref):
            refs.append(r)
    return refs


def external_refs(doc: Document) -> list[Reference]:
    """Return all references that point to external Truss repositories."""
    refs = []
    for r in doc.assumes:
        if is_external_ref(r.ref):
            refs.append(r)
    for r in doc.evidence:
        if is_external_ref(r.ref):
            refs.append(r)
    return refs


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_build_deps(args):
    """Build the reverse dependency index."""
    root = repo_root()
    docs = find_documents(root)

    # Forward map: target -> [source, ...]
    reverse: dict[str, list[str]] = defaultdict(list)

    for doc in docs:
        for ref in internal_refs(doc):
            reverse[ref.ref].append(doc.path)

    # Write deps.yaml
    deps_path = root / ".truss" / "deps.yaml"
    deps_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# .truss/deps.yaml (generated, do not edit)",
        "# Reverse dependency index: target -> list of documents that reference it",
        "# Rebuilt by scripts/truss.py build-deps",
    ]

    if reverse:
        for target in sorted(reverse):
            lines.append(f"{target}:")
            for source in sorted(set(reverse[target])):
                lines.append(f"  - {source}")
    else:
        lines.append("# (no dependencies found)")

    deps_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Dependency index written to {deps_path}")


def cmd_detect_stale(args):
    """Identify documents with out-of-date pinned references."""
    root = repo_root()
    docs = find_documents(root)
    check_remote = getattr(args, "remote", False)

    @dataclass
    class StaleEntry:
        document: str
        dependency: str
        pinned_hash: str
        current_hash: str
        status: str  # "stale", "missing", or "external"

    stale_entries: list[StaleEntry] = []
    skipped_external = 0

    for doc in docs:
        # Check local refs as before
        for ref in internal_refs(doc):
            if not ref.pin:
                continue
            current = git_file_hash(root, ref.ref)
            if current is None:
                stale_entries.append(StaleEntry(doc.path, ref.ref, ref.pin, "(missing)", "missing"))
            elif not current.startswith(ref.pin) and not ref.pin.startswith(current):
                stale_entries.append(StaleEntry(doc.path, ref.ref, ref.pin, current, "stale"))

        # Handle external refs
        ext_refs = external_refs(doc)
        if ext_refs and not check_remote:
            skipped_external += len(ext_refs)
        elif ext_refs and check_remote:
            for ref in ext_refs:
                if not ref.pin:
                    continue
                # For remote checking, we note these as external but cannot
                # verify without cloning the remote repo
                stale_entries.append(
                    StaleEntry(doc.path, ref.ref, ref.pin, "(remote — not verified)", "external")
                )

    # Write stale.yaml
    stale_path = root / ".truss" / "stale.yaml"
    stale_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# .truss/stale.yaml (generated, do not edit)",
        "# Documents with out-of-date pinned references",
        "# Rebuilt by scripts/truss.py detect-stale",
    ]

    if stale_entries:
        lines.append("stale:")
        for e in stale_entries:
            lines.append(f"  - document: {e.document}")
            lines.append(f"    dependency: {e.dependency}")
            lines.append(f"    pinned_hash: {e.pinned_hash}")
            lines.append(f"    current_hash: {e.current_hash}")
            lines.append(f"    status: {e.status}")
    else:
        lines.append("stale: []")

    stale_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Staleness check complete: {len(stale_entries)} stale reference(s) found.")
    print(f"Results written to {stale_path}")

    if skipped_external:
        print(f"Skipped {skipped_external} external reference(s). Use --remote to include them.")

    if stale_entries:
        print()
        print("Stale documents:")
        for e in stale_entries:
            print(f"  {e.document} -> {e.dependency} (pinned: {e.pinned_hash}, current: {e.current_hash})")
        sys.exit(1)


def cmd_validate(args):
    """Validate documents against kind-specific rules."""
    root = repo_root()
    docs = find_documents(root)

    errors = 0
    warnings = 0

    def error(doc_path, msg):
        nonlocal errors
        print(f"  \033[0;31mERROR:\033[0m {msg}")
        errors += 1

    def warn(doc_path, msg):
        nonlocal warnings
        print(f"  \033[1;33mWARN:\033[0m {msg}")
        warnings += 1

    for doc in docs:
        print(f"Checking: {doc.path}")

        # Check frontmatter exists
        if not doc.raw_frontmatter:
            error(doc.path, "Missing or empty YAML frontmatter")
            continue

        # Check kind
        if not doc.kind:
            error(doc.path, "Missing 'kind' field in frontmatter")
            continue

        # Check kind matches directory
        expected_kind = doc.path.split("/")[0]
        if doc.kind != expected_kind:
            error(doc.path, f"Kind '{doc.kind}' does not match directory '{expected_kind}'")

        # Required fields
        if not doc.id:
            error(doc.path, "Missing 'id' field")
        if not doc.title:
            error(doc.path, "Missing 'title' field")
        if not doc.created:
            error(doc.path, "Missing 'created' field")

        # Kind-specific rules
        if doc.kind == "ground":
            if not doc.evidence:
                warn(doc.path, "Ground document has no evidence")
            if doc.assumes:
                error(doc.path, "Ground document must not have 'assumes'")
            # Check for internal refs in evidence
            for ref in doc.evidence:
                if INTERNAL_REF_RE.match(ref.ref) and not is_external_ref(ref.ref):
                    error(doc.path, f"Ground document references internal doc {ref.ref} as evidence")

        elif doc.kind == "hypothetical":
            if not doc.assumes:
                warn(doc.path, "Hypothetical document has no assumes")

        elif doc.kind == "generic":
            if not doc.parameter:
                warn(doc.path, "Generic document has no 'parameter' field")

        # Check that local referenced files exist (skip external refs)
        for ref in internal_refs(doc):
            ref_path = root / ref.ref
            if not ref_path.exists():
                error(doc.path, f"Referenced file does not exist: {ref.ref}")

        # Report external refs as info (not errors)
        ext = external_refs(doc)
        if ext:
            for ref in ext:
                print(f"  \033[0;36mINFO:\033[0m External ref: {ref.ref} (pin: {ref.pin or 'none'})")

    print()
    print("\u2501" * 40)
    print(f"Checked: {len(docs)} documents")
    print(f"Errors:  \033[0;31m{errors}\033[0m")
    print(f"Warnings: \033[1;33m{warnings}\033[0m")

    if errors > 0:
        print("\033[0;31mValidation failed.\033[0m")
        sys.exit(1)
    print("\033[0;32mValidation passed.\033[0m")


def cmd_resolve(args):
    """Interactive resolution workflow for stale documents."""
    root = repo_root()

    # First detect staleness
    docs = find_documents(root)

    @dataclass
    class StaleInfo:
        document: str
        dependency: str
        pinned_hash: str
        current_hash: str

    stale_map: dict[str, list[StaleInfo]] = defaultdict(list)

    for doc in docs:
        for ref in internal_refs(doc):
            if not ref.pin:
                continue
            current = git_file_hash(root, ref.ref)
            if current is None:
                stale_map[doc.path].append(StaleInfo(doc.path, ref.ref, ref.pin, "(missing)"))
            elif not current.startswith(ref.pin) and not ref.pin.startswith(current):
                stale_map[doc.path].append(StaleInfo(doc.path, ref.ref, ref.pin, current))

    if not stale_map:
        print("\033[0;32mNo stale documents found. Nothing to resolve.\033[0m")
        return

    print(f"\033[0;34mTruss Resolution Workflow\033[0m")
    print("=" * 40)
    print(f"\n{len(stale_map)} document(s) with stale references.\n")

    # Topological sort: resolve docs whose stale deps are not themselves stale first
    stale_docs = set(stale_map.keys())
    resolved = set()
    order = []

    # Simple topo sort with rounds
    remaining = set(stale_docs)
    while remaining:
        ready = []
        for doc_path in remaining:
            deps_stale = False
            for info in stale_map[doc_path]:
                if info.dependency in remaining - resolved:
                    deps_stale = True
                    break
            if not deps_stale:
                ready.append(doc_path)

        if not ready:
            # Cycle or all deps are stale — just pick remaining
            ready = sorted(remaining)

        order.extend(sorted(ready))
        remaining -= set(ready)

    for doc_path in order:
        infos = stale_map[doc_path]
        separator = '\u2501' * 55
        print(f"\033[1;33m{separator}\033[0m")
        print(f"Resolving: \033[0;34m{doc_path}\033[0m")
        for info in infos:
            print(f"  Stale dep: {info.dependency} (pinned: {info.pinned_hash}, current: {info.current_hash})")
            if info.current_hash != "(missing)":
                diff = git_diff(root, info.pinned_hash, info.dependency)
                if diff:
                    # Show abbreviated diff
                    diff_lines = diff.split("\n")
                    if len(diff_lines) > 30:
                        print("  Diff (truncated):")
                        print("\n".join("    " + l for l in diff_lines[:30]))
                        print(f"    ... ({len(diff_lines) - 30} more lines)")
                    else:
                        print("  Diff:")
                        print("\n".join("    " + l for l in diff_lines))

        print()
        print("  [c] Confirm  — re-pin only, conclusions unaffected")
        print("  [u] Update   — edit document, then re-pin")
        print("  [i] Invalidate — mark as invalidated")
        print("  [s] Skip     — defer to later")
        print()

        action = input(f"  Action for {doc_path} [c/u/i/s]: ").strip().lower()

        if action == "c":
            repin_document(root, doc_path)
            subprocess.run(["git", "-C", str(root), "add", doc_path], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", f"truss: confirm {doc_path} (re-pin dependencies)"],
                check=True,
            )
            print("\033[0;32mConfirmed and re-pinned.\033[0m\n")
            resolved.add(doc_path)

        elif action == "u":
            editor = os.environ.get("EDITOR", "vi")
            subprocess.run([editor, str(root / doc_path)])
            repin_document(root, doc_path)
            subprocess.run(["git", "-C", str(root), "add", doc_path], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", f"truss: update {doc_path} (revised after dependency change)"],
                check=True,
            )
            print("\033[0;32mUpdated and re-pinned.\033[0m\n")
            resolved.add(doc_path)

        elif action == "i":
            reason = input("  Reason for invalidation: ").strip()
            filepath = root / doc_path
            content = filepath.read_text(encoding="utf-8")
            # Insert status fields before closing ---
            content = content.replace(
                "\n---\n",
                f"\nstatus: invalidated\ninvalidation_reason: \"{reason}\"\n---\n",
                1,
            )
            filepath.write_text(content, encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", doc_path], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", f"truss: invalidate {doc_path} — {reason}"],
                check=True,
            )
            print("\033[0;31mDocument invalidated.\033[0m\n")
            resolved.add(doc_path)

        elif action == "s":
            print("\033[1;33mSkipped.\033[0m\n")

        else:
            print("Unknown action, skipping.\n")

    # Rebuild deps
    print("\nRebuilding dependency index...")
    cmd_build_deps(args)
    print("\n\033[0;32mResolution complete.\033[0m")


def repin_document(root: Path, doc_path: str):
    """Update all pinned hashes in a document to current HEAD values."""
    filepath = root / doc_path
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")
    result = []

    pending_ref = None
    in_frontmatter = False
    past_first = False

    for line in lines:
        if line.strip() == "---":
            if not past_first:
                past_first = True
                in_frontmatter = True
                result.append(line)
                continue
            else:
                in_frontmatter = False
                result.append(line)
                pending_ref = None
                continue

        if not in_frontmatter:
            result.append(line)
            continue

        # Track ref lines
        ref_match = re.search(r"ref:\s*((?:ground|hypothetical|generic)/.+?)(?:\s*$)", line)
        if ref_match:
            pending_ref = ref_match.group(1).strip()
            result.append(line)
            continue

        # Update pin lines
        pin_match = re.match(r"^(\s*)pin:\s*[a-f0-9]+", line)
        if pin_match and pending_ref:
            indent = pin_match.group(1)
            new_hash = git_file_hash(root, pending_ref) or "0000000"
            result.append(f"{indent}pin: {new_hash}")
            pending_ref = None
            continue

        # Non-blank, non-continuation line clears pending ref
        if line.strip() and not re.match(r"^\s+(pin|note|type|repo):", line):
            pending_ref = None

        result.append(line)

    filepath.write_text("\n".join(result), encoding="utf-8")


def cmd_new(args):
    """Create a new Truss document."""
    root = repo_root()
    from datetime import date

    kind = args.kind
    doc_id = args.id
    title = args.title
    today = date.today().isoformat()

    if kind == "ground":
        dirpath = root / "ground"
        content = textwrap.dedent(f"""\
            ---
            kind: ground
            id: {doc_id}
            title: {title}
            created: {today}
            evidence:
              - type: url
                ref: TODO
            ---

            # {title}

            TODO: Document the observable facts here.
        """)
    elif kind == "hypothetical":
        dirpath = root / "hypothetical"
        content = textwrap.dedent(f"""\
            ---
            kind: hypothetical
            id: {doc_id}
            title: {title}
            created: {today}
            assumes:
              - ref: ground/TODO.md
                pin: 0000000
                note: "TODO: why this dependency matters"
            ---

            # {title}

            TODO: Document the conditional reasoning here.
        """)
    elif kind == "generic":
        dirpath = root / "generic"
        content = textwrap.dedent(f"""\
            ---
            kind: generic
            id: {doc_id}
            title: {title}
            created: {today}
            parameter: "TODO: what kind of thing this applies to"
            evidence:
              - type: citation
                ref: "TODO"
            ---

            # {title}

            TODO: Document the general principle here.
        """)
    else:
        print(f"Unknown kind: {kind}. Must be ground, hypothetical, or generic.")
        sys.exit(1)

    dirpath.mkdir(parents=True, exist_ok=True)
    filepath = dirpath / f"{doc_id}.md"
    filepath.write_text(content, encoding="utf-8")
    print(f"Created {filepath.relative_to(root)}")


def cmd_add_remote(args):
    """Register a remote Truss repository in .truss/config.yaml."""
    root = repo_root()
    config = load_config(root)

    remotes = config.get("remotes", {})
    if isinstance(remotes, str) and remotes == "":
        remotes = {}
    remotes[args.name] = args.url
    config["remotes"] = remotes

    save_config(root, config)
    print(f"Remote '{args.name}' registered: {args.url}")


def cmd_list_remotes(args):
    """List registered remote Truss repositories."""
    root = repo_root()
    config = load_config(root)

    remotes = config.get("remotes", {})
    if not remotes or (isinstance(remotes, str) and remotes == ""):
        print("No remotes registered.")
        print("Add one with: python3 scripts/truss.py add-remote <name> <url>")
        return

    print("Registered remotes:")
    for name, url in remotes.items():
        print(f"  {name}: {url}")


def cmd_init(args):
    """Initialize a new Truss project."""
    project_name = args.name
    target = Path(args.name).resolve()

    if target.exists():
        print(f"Error: directory '{project_name}' already exists.")
        sys.exit(1)

    # Determine the source template directory (this repo)
    script_dir = Path(__file__).resolve().parent
    template_root = script_dir.parent

    print(f"Initializing new Truss project: {project_name}")

    # Create project directory
    target.mkdir(parents=True)

    # Copy framework files
    # scripts/
    scripts_dst = target / "scripts"
    scripts_dst.mkdir()
    shutil.copy2(template_root / "scripts" / "truss.py", scripts_dst / "truss.py")

    # .truss/config.yaml (fresh, with no sample data)
    truss_dir = target / ".truss"
    truss_dir.mkdir()
    config_content = textwrap.dedent("""\
        # Truss project configuration
        version: "1.0"

        # Document kind directories
        kinds:
          ground: ground/
          hypothetical: hypothetical/
          generic: generic/

        # Generated artifact paths
        generated:
          deps: .truss/deps.yaml
          stale: .truss/stale.yaml

        # Remote Truss repositories
        # Register with: python3 scripts/truss.py add-remote <name> <url>
        remotes: {}

        # Validation settings
        validation:
          # Require evidence on ground documents
          require_ground_evidence: true
          # Require assumes on hypothetical documents
          require_hypothetical_assumes: true
          # Require parameter on generic documents
          require_generic_parameter: true
    """)
    (truss_dir / "config.yaml").write_text(config_content, encoding="utf-8")

    # .gitignore
    gitignore_content = textwrap.dedent("""\
        # Generated artifacts (rebuilt by scripts)
        .truss/deps.yaml
        .truss/stale.yaml
    """)
    (target / ".gitignore").write_text(gitignore_content, encoding="utf-8")

    # Create kind directories with .gitkeep
    for kind_dir in ("ground", "hypothetical", "generic"):
        d = target / kind_dir
        d.mkdir()
        (d / ".gitkeep").write_text("", encoding="utf-8")

    # README
    readme_content = textwrap.dedent(f"""\
        # {project_name}

        A knowledge base built with the [Truss](https://github.com/your-org/Truss) framework.

        ## Quick Start

        ```bash
        # Create documents
        python3 scripts/truss.py new ground g-example "Example Ground Document"
        python3 scripts/truss.py new hypothetical h-example "Example Hypothesis"

        # Validate all documents
        python3 scripts/truss.py validate

        # Build the reverse dependency index
        python3 scripts/truss.py build-deps

        # Detect stale references
        python3 scripts/truss.py detect-stale
        ```

        ## Document Kinds

        | Kind | Directory | Answers |
        |------|-----------|---------|
        | **Ground** | `ground/` | "What is the case?" |
        | **Hypothetical** | `hypothetical/` | "What follows from what we know?" |
        | **Generic** | `generic/` | "What is generally true about things like this?" |
    """)
    (target / "README.md").write_text(readme_content, encoding="utf-8")

    # Initialize git and make initial commit
    subprocess.run(["git", "init", str(target)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(target), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(target), "commit", "-m", "Initialize Truss project"],
        check=True, capture_output=True,
    )

    print(f"Truss project created at: {target}")
    print(f"  {len(list(target.rglob('*')))} files committed.")
    print()
    print("Next steps:")
    print(f"  cd {project_name}")
    print("  python3 scripts/truss.py new ground g-example \"My First Ground Document\"")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Truss — Knowledge engineering framework CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Commands:
              build-deps     Build the reverse dependency index (.truss/deps.yaml)
              detect-stale   Identify stale pinned references (.truss/stale.yaml)
              validate       Validate all documents against kind-specific rules
              resolve        Interactive resolution workflow for stale documents
              new            Create a new document with proper frontmatter
              add-remote     Register a remote Truss repository
              list-remotes   List registered remote Truss repositories
              init           Initialize a new Truss project from template
        """),
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("build-deps", help="Build reverse dependency index")

    stale_parser = sub.add_parser("detect-stale", help="Detect stale pinned references")
    stale_parser.add_argument(
        "--remote", action="store_true", default=False,
        help="Include external (cross-repo) references in staleness check",
    )

    sub.add_parser("validate", help="Validate all documents")
    sub.add_parser("resolve", help="Interactive stale resolution workflow")

    new_parser = sub.add_parser("new", help="Create a new document")
    new_parser.add_argument("kind", choices=["ground", "hypothetical", "generic"])
    new_parser.add_argument("id", help="Document ID (e.g., g-api-shape)")
    new_parser.add_argument("title", help="Document title")

    remote_parser = sub.add_parser("add-remote", help="Register a remote Truss repo")
    remote_parser.add_argument("name", help="Short name for the remote (e.g., infra-truss)")
    remote_parser.add_argument("url", help="Git URL of the remote Truss repo")

    sub.add_parser("list-remotes", help="List registered remote Truss repos")

    init_parser = sub.add_parser("init", help="Initialize a new Truss project")
    init_parser.add_argument("name", help="Project name (creates a new directory)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "build-deps": cmd_build_deps,
        "detect-stale": cmd_detect_stale,
        "validate": cmd_validate,
        "resolve": cmd_resolve,
        "new": cmd_new,
        "add-remote": cmd_add_remote,
        "list-remotes": cmd_list_remotes,
        "init": cmd_init,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
