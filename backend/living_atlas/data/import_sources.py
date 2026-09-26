"""Operator CLI: import only the frozen, allowlisted development literature."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import SourceCatalog, fetch_verified


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="data/manifests/showcase.json")
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--download", action="store_true", help="Fetch the pinned corpus if absent (660 MB)")
    parser.add_argument("--ontologies", action="store_true", help="Also fetch and verify pinned anatomy/stage files")
    args = parser.parse_args()
    catalog = SourceCatalog.from_manifest(args.manifest, cache_dir=args.cache_dir, download=args.download)
    manifest = catalog.manifest
    cache = Path(args.cache_dir) if args.cache_dir else Path(args.manifest).resolve().parent.parent / "raw/flyaoc"
    # The original article-rights manifest is retained as a separate verified
    # input. Runtime retrieval never traverses this file or ontology files.
    names = ["pmc_license_manifest.jsonl"]
    if args.ontologies:
        names.extend(name for name, spec in manifest["dataset"]["files"].items() if spec["role"] == "ontology")
    verified = []
    for name in names:
        spec = manifest["dataset"]["files"][name]
        target = cache / name
        if args.download or target.exists():
            dataset = manifest["dataset"]
            fetch_verified(f"https://huggingface.co/datasets/{dataset['repository']}/resolve/{dataset['revision']}/{name}", target, spec["sha256"])
            verified.append(name)
    print(json.dumps({
        "manifest_sha256": catalog.manifest_sha256,
        "dataset_revision": manifest["dataset"]["revision"],
        "source_count": len(catalog.sources), "chunk_count": len(catalog.chunks),
        "sources": [{"source_id": source["source_id"], "source_version": source["source_version"],
                     "distribution_status": source["distribution_status"]} for source in catalog.sources],
        "verified_auxiliary_files": verified,
        "cache_dir": str(cache.resolve()), "gold_labels_downloaded": False,
        "status": "source_import_complete; application_E2E_not_claimed",
    }, indent=2))


if __name__ == "__main__":
    main()
