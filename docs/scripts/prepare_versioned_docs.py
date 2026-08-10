"""Prepare versioned documentation folders after a Sphinx build."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import urllib.error
import urllib.request
from pathlib import Path


def _copy_tree(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=_ignore_published_dirs)


def _ignore_published_dirs(source: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name == "main" or re.fullmatch(r"v[0-9][0-9.]*", name):
            ignored.add(name)
    return ignored


def _read_published_manifest(manifest_url: str) -> dict[str, object]:
    with urllib.request.urlopen(manifest_url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_versions_from_file(path: Path) -> list[str]:
    if not path or not path.exists():
        return []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    existing = manifest.get("versions", []) if isinstance(manifest, dict) else []
    return [str(v).strip() for v in existing if str(v).strip()]


def _collect_versions(
    existing_path: Path, published_manifest_url: str, release_version: str
) -> list[str]:
    versions = _read_versions_from_file(existing_path)  # lokal / gh-pages
    if not versions and published_manifest_url:  # Fallback HTTP
        try:
            manifest = _read_published_manifest(published_manifest_url)
            versions = [
                str(v).strip() for v in manifest.get("versions", []) if str(v).strip()
            ]
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            versions = []
    if release_version and release_version not in versions:
        versions.insert(0, release_version)
    return versions


def _write_versions_manifest(
    build_dir: Path, versions: list[str], release_version: str
) -> None:
    latest = versions[0] if versions else release_version
    manifest = {"main": "main", "latest": latest, "versions": versions}
    (build_dir / "versions.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default="./build")
    parser.add_argument(
        "--release-version", default=os.environ.get("DOCS_RELEASE_VERSION", "")
    )
    parser.add_argument(
        "--published-versions-url",
        default=os.environ.get("DOCS_PUBLISHED_VERSIONS_URL", ""),
    )
    parser.add_argument("--existing-manifest", default=None)
    args = parser.parse_args()

    build_dir = Path(args.build_dir).resolve()
    if not build_dir.exists():
        raise SystemExit(f"Build directory does not exist: {build_dir}")

    release_version = args.release_version.strip()
    published_versions_url = args.published_versions_url.strip()

    # only update the versions.json manifest if a release version is provided
    existing_path = (
        Path(args.existing_manifest)
        if args.existing_manifest
        else (build_dir / "versions.json")
    )
    if release_version:
        versions = _collect_versions(
            existing_path, published_versions_url, release_version
        )
        _write_versions_manifest(build_dir, versions, release_version)
        release_dir = build_dir / release_version
        _copy_tree(build_dir, release_dir)  # ignoriert preview/ und vX-Ordner

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
