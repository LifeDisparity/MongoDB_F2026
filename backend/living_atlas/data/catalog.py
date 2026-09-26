"""Deterministic source import from an explicit FlyAOC article allowlist.

Only literature and rights files are fetched. Benchmark labels, summaries and
gold answers are never downloaded or exposed by this module.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import tempfile
from urllib.request import Request, urlopen


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_verified(url: str, target: Path, expected: str) -> None:
    """Publish a completed download only after its full SHA-256 matches."""
    if target.exists():
        if file_sha256(target) != expected:
            raise ValueError(f"Cached file hash mismatch: {target.name}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            request = Request(url, headers={"User-Agent": "LivingAtlas-source-import/1"})
            with urlopen(request, timeout=60) as response:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    stream.write(block)
            stream.flush()
            if file_sha256(temporary) != expected:
                raise ValueError(f"Downloaded file hash mismatch: {target.name}")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)


def canonical_source(record: dict, entry: dict) -> tuple[dict, list[dict]]:
    """Source offsets use Unicode code points in this normalized paragraph text.

    Paragraph text is unchanged. Title, abstract, and sorted section types are
    joined with exactly two newlines. Evidence offsets are separately relative
    to their chunk. The transform version is frozen in the manifest.
    """
    if set(record) != {"pmcid", "title", "abstract", "sections"}:
        raise ValueError("Unexpected corpus fields; refusing potential answer leakage")
    if record["pmcid"] != entry["source_id"]:
        raise ValueError("Source identity mismatch")
    if not isinstance(record["title"], str) or not isinstance(record["abstract"], str):
        raise ValueError("Invalid title or abstract")
    if not isinstance(record["sections"], dict):
        raise ValueError("Invalid source sections")
    paragraphs = [("TITLE", record["title"]), ("ABSTRACT", record["abstract"])]
    for section_type, values in sorted(record["sections"].items()):
        if not isinstance(section_type, str) or not isinstance(values, list):
            raise ValueError("Invalid section type or paragraphs")
        if any(not isinstance(value, str) for value in values):
            raise ValueError("Invalid paragraph")
        paragraphs.extend((section_type, value) for value in values)
    paragraphs = [(kind, value) for kind, value in paragraphs if value.strip()]
    text = "\n\n".join(value for _, value in paragraphs)
    version = sha256(text.encode("utf-8")).hexdigest()
    if entry.get("content_sha256") and entry["content_sha256"] != version:
        raise ValueError("Normalized source hash mismatch")
    source_id = entry["source_id"]
    chunks, sections, offset = [], [], 0
    for index, (kind, value) in enumerate(paragraphs):
        chunk_id = f"{source_id}:{version}:p{index:04d}"
        section = {
            "section_id": f"{source_id}:{kind}", "section_type": kind,
            "section_title": kind, "chunk_id": chunk_id,
            "start_offset": offset, "end_offset": offset + len(value),
        }
        chunks.append({
            **section, "chunk_id": chunk_id, "source_id": source_id,
            "source_version": version, "text": value,
            "content_sha256": sha256(value.encode("utf-8")).hexdigest(),
        })
        sections.append(section)
        offset += len(value) + 2
    source = {
        "source_id": source_id, "source_version": version,
        "content_sha256": version, "title": record["title"],
        "original_url": entry["original_url"], "pmcid": source_id,
        "license_id": entry["license_id"], "license_url": entry["license_url"],
        "distribution_status": entry["distribution_status"],
        "sections": sections, "gene_ids": entry["gene_ids"],
        "rights_note": entry["rights_note"],
        "transform_version": "flyaoc_paragraphs_v1",
    }
    return source, chunks


class SourceCatalog:
    """Only allowlisted immutable sources; callers receive detached records."""

    def __init__(self, manifest: dict, records: dict[str, dict]):
        self.manifest = deepcopy(manifest)
        self.manifest_sha256 = sha256(json.dumps(
            manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")).hexdigest()
        self._sources, self._chunks = {}, {}
        self._gene_sources: dict[str, set[str]] = {}
        for entry in manifest["sources"]:
            source, chunks = canonical_source(records[entry["source_id"]], entry)
            if source["source_id"] in self._sources:
                raise ValueError("Duplicate source identity")
            self._sources[source["source_id"]] = source
            self._chunks.update({chunk["chunk_id"]: chunk for chunk in chunks})
            for gene_id in entry["gene_ids"]:
                self._gene_sources.setdefault(gene_id, set()).add(source["source_id"])

    @classmethod
    def from_manifest(cls, path: str | Path, cache_dir: str | Path | None = None,
                      download: bool = False) -> "SourceCatalog":
        path = Path(path).resolve()
        if path.is_dir():
            path = path / "data/manifests/showcase.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 1 or manifest.get("transform_version") != "flyaoc_paragraphs_v1":
            raise ValueError("Unsupported source manifest version")
        dataset = manifest["dataset"]
        if dataset["repository"] != "anonymous-042/flyaoc" or not re.fullmatch(r"[0-9a-f]{40}", dataset["revision"]):
            raise ValueError("Dataset must use the approved repository and a full commit pin")
        cache = Path(cache_dir) if cache_dir else path.parent.parent / "raw/flyaoc"
        records = {}
        entries = {row["source_id"]: row for row in manifest["sources"]}
        if len(entries) != len(manifest["sources"]):
            raise ValueError("Duplicate source manifest entries")
        for source_id, entry in entries.items():
            if not re.fullmatch(r"PMC[0-9]+", source_id):
                raise ValueError("Invalid PMCID")
            selected = cache / "selected" / f"{source_id}-{entry['record_sha256']}.json"
            if selected.exists():
                raw = selected.read_bytes()
                if sha256(raw).hexdigest() != entry["record_sha256"]:
                    raise ValueError("Selected source cache hash mismatch")
                records[source_id] = json.loads(raw)
        if len(records) != len(entries):
            spec = dataset["files"]["corpus.jsonl"]
            corpus = cache / "corpus.jsonl"
            if not corpus.exists() and not download:
                raise FileNotFoundError("Pinned corpus not cached; run python -m living_atlas.data.import_sources --download")
            url = f"https://huggingface.co/datasets/{dataset['repository']}/resolve/{dataset['revision']}/corpus.jsonl"
            fetch_verified(url, corpus, spec["sha256"])
            with corpus.open("rb") as stream:
                for line in stream:
                    raw = line.rstrip(b"\r\n")
                    record = json.loads(raw)
                    source_id = record.get("pmcid")
                    if source_id not in entries:
                        continue
                    entry = entries[source_id]
                    if sha256(raw).hexdigest() != entry["record_sha256"]:
                        raise ValueError(f"Pinned article record mismatch: {source_id}")
                    if source_id in records:
                        if records[source_id] != record:
                            raise ValueError("Duplicate differing source records")
                        continue
                    records[source_id] = record
                    selected = cache / "selected" / f"{source_id}-{entry['record_sha256']}.json"
                    selected.parent.mkdir(parents=True, exist_ok=True)
                    selected.write_bytes(raw)
            if set(records) != set(entries):
                raise ValueError("Some manifest sources are missing from the corpus")
        return cls(manifest, records)

    @property
    def sources(self) -> list[dict]:
        return deepcopy(list(self._sources.values()))

    @property
    def chunks(self) -> list[dict]:
        return deepcopy(list(self._chunks.values()))

    def get_source(self, source_id: str) -> dict:
        if source_id not in self._sources:
            raise ValueError("Unknown source")
        return deepcopy(self._sources[source_id])

    def get_chunk(self, chunk_id: str, source_version: str) -> dict:
        chunk = self._chunks.get(chunk_id)
        if chunk is None:
            raise ValueError("Unknown chunk")
        if chunk["source_version"] != source_version:
            raise ValueError("Source version mismatch")
        if sha256(chunk["text"].encode("utf-8")).hexdigest() != chunk["content_sha256"]:
            raise ValueError("Chunk integrity mismatch")
        return deepcopy(chunk)

    def gene_source_ids(self, gene_id: str) -> set[str]:
        if gene_id not in self._gene_sources:
            raise ValueError("Gene ID is outside the selected corpus")
        return set(self._gene_sources[gene_id])
