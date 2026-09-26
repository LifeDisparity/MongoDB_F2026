"""Explicit synthetic engineering fixture, never a scientific measurement."""
from hashlib import sha256

def availability_fixture(run_id: str) -> dict:
    sources, chunks, evidence = [], [], []
    descriptions = {
        "S1": "Synthetic source S1 supports engineering claims A and B.",
        "S2": "Synthetic source S2 independently supports engineering claim B.",
        "S3": "Synthetic source S3 supports engineering claim C.",
    }
    for source_id, text in descriptions.items():
        digest = sha256(text.encode()).hexdigest()
        chunk_id = f"{source_id}:chunk:0"
        sources.append({
            "source_id": source_id, "source_version": digest,
            "title": f"{source_id} · Synthetic engineering source",
            "original_url": f"https://example.org/living-atlas/fixtures/{source_id}",
            "content_sha256": digest, "license_id": "CC0-1.0",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "distribution_status": "synthetic_fixture",
            "sections": [{"section_id": "fixture", "title": "Engineering fixture", "section_type": "results"}],
            "gene_ids": ["fixture-gene-1" if source_id != "S3" else "fixture-gene-2"],
        })
        chunks.append({
            "chunk_id": chunk_id, "source_id": source_id, "source_version": digest,
            "text": text, "start_offset": 0, "end_offset": len(text),
            "content_sha256": digest,
            "section_type": "results", "section_title": "Engineering fixture",
        })
        evidence.append({
            "evidence_id": "E" + source_id[1:], "source_id": source_id,
            "source_version": digest, "chunk_id": chunk_id,
            "span_id": f"fixture:{source_id}:0:{len(text)}",
            "start_offset": 0, "end_offset": len(text), "quote_sha256": digest,
        })
    claims = []
    for claim_id, refs, gene, description in [
        ("A", ["E1"], "fixture-gene-1", "Claim A · support from S1 only"),
        ("B", ["E1", "E2"], "fixture-gene-1", "Claim B · independent support from S1 + S2"),
        ("C", ["E3"], "fixture-gene-2", "Claim C · unrelated support from S3"),
    ]:
        claims.append({
            "claim_id": claim_id, "run_id": run_id, "revision": 0, "gene_id": gene,
            "relation": "expressed_in", "object_id": None, "object_label": description,
            "qualifiers": {
                "polarity": "observed", "assay": "Synthetic engineering fixture",
                "scope_notes": "Not a biological assertion or measured model result.",
            },
            "evidence_ids": refs, "conflicting_evidence_ids": [],
            "usable_evidence_ids": refs, "usable_conflicting_evidence_ids": [],
            "status": "supported", "policy_version": "fixture-v1",
        })
    return dict(sources=sources, chunks=chunks, evidence=evidence, claims=claims)
