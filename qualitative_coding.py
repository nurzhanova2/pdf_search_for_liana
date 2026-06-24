#!/usr/bin/env python3
import argparse
import csv
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "pdf_search.db"
CODES_PATH = HERE / "codes.json"
SOURCE_TYPES_PATH = HERE / "source_types.json"
OUTPUT_DIR = HERE / "analysis_output"
SENTENCE = re.compile(r"(?<!\b[A-ZА-ЯЁ])(?<=[.!?])\s+(?=[A-ZА-ЯЁ0-9])")

CONSTRUCT_CLAIMS = {
    "institutional_fragmentation": "Formal texts indicate fragmentation when mandates, procedures, or standards are distributed unevenly across institutions.",
    "cooperation_incentives_constraints": "Formal texts indicate cooperation interest or constraint through duties, incentives, limits, and access rules for interagency work.",
    "coordination_mechanisms": "Formal texts indicate coordination capacity through information-sharing channels, lead authority, escalation, and incident-response routines.",
    "csg_outcomes": "Formal texts indicate CSG quality through policy coherence, implementation capacity, response coordination, and accountability.",
    "dynamic_capabilities": "Formal texts indicate sensing, seizing, and transforming routines that connect governance design to operational performance.",
    "governance_failure_modes": "Formal texts indicate governance failure modes where gaps, weak escalation, or missing follow-through appear repeatedly.",
}

PRIMARY_DOCUMENTARY_TYPES = {
    "law",
    "strategy",
    "regulation",
    "institutional_protocol",
    "government_guidance",
    "government_report",
    "government_communication",
    "institutional_report",
}

TRIANGULATION_TYPES = {"international_report", "institutional_interview"}


DESIGN_REQUIREMENTS = {
    "institutional_fragmentation": "Reduce role ambiguity and align mandates, procedures, and standards across institutions.",
    "cooperation_incentives_constraints": "Create incentives and trusted rules for sustained interagency cooperation and lawful information access.",
    "coordination_mechanisms": "Formalize lead authority, escalation paths, shared reporting channels, and incident playbooks.",
    "csg_outcomes": "Link strategies and regulations to operational readiness, accountability, and remediation closure.",
    "dynamic_capabilities": "Institutionalize sensing, seizing, and transforming routines through monitoring, funded plans, exercises, and review cycles.",
    "governance_failure_modes": "Treat repeated inconsistencies and gaps as design inputs for clearer governance roles and routines.",
}


def load_codes(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_source_types(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def source_type(document, overrides):
    if document in overrides:
        return overrides[document]
    name = document.lower()
    if any(word in name for word in ("law", "закон", "kodeks", "code")):
        return "law"
    if any(word in name for word in ("strategy", "concept", "стратег", "концепц")):
        return "strategy"
    if any(word in name for word in ("rule", "order", "regulation", "приказ", "правил", "регламент", "постанов")):
        return "regulation"
    if any(word in name for word in ("protocol", "procedure", "instruction", "протокол", "процедур", "инструкц")):
        return "institutional_protocol"
    return "document"


def evidence_role(source_type_name):
    if source_type_name in PRIMARY_DOCUMENTARY_TYPES:
        return "primary_documentary"
    if source_type_name in TRIANGULATION_TYPES:
        return "triangulation"
    return "contextual_literature"


def document_inventory(connection, overrides):
    rows = connection.execute("SELECT DISTINCT document FROM pages ORDER BY document COLLATE NOCASE")
    inventory = []
    for (document,) in rows:
        kind = source_type(document, overrides)
        inventory.append({"document": document, "source_type": kind, "evidence_role": evidence_role(kind)})
    return inventory


def iter_sentences(connection):
    rows = connection.execute(
        "SELECT document, page, text FROM pages WHERE length(text) > 0 "
        "ORDER BY document COLLATE NOCASE, page"
    )
    for document, page, text in rows:
        for sentence in SENTENCE.split(text):
            clean = sentence.strip()
            if clean:
                yield document, page, clean


def matched_terms(sentence, keywords):
    lower = sentence.lower()
    return [keyword for keyword in keywords if keyword.lower() in lower]


def code_evidence(connection, codes, overrides):
    evidence = []
    for document, page, sentence in iter_sentences(connection):
        for code in codes:
            matches = matched_terms(sentence, code["keywords"])
            if not matches:
                continue
            kind = source_type(document, overrides)
            evidence.append({
                "document": document,
                "source_type": kind,
                "evidence_role": evidence_role(kind),
                "page": page,
                "sentence": sentence,
                "code_id": code["code_id"],
                "code_label": code["label"],
                "code_type": code["code_type"],
                "construct": code["construct"],
                "matched_terms": "; ".join(matches),
            })
    return evidence


def claim_rows(evidence):
    grouped = defaultdict(list)
    for row in evidence:
        grouped[row["construct"]].append(row)

    rows = []
    for construct, items in sorted(grouped.items()):
        documents = sorted({item["document"] for item in items})
        source_types = sorted({item["source_type"] for item in items})
        primary_items = [item for item in items if item["evidence_role"] == "primary_documentary"]
        primary_documents = sorted({item["document"] for item in primary_items})
        primary_source_types = sorted({item["source_type"] for item in primary_items})
        supported = len(primary_documents) >= 2 or len(primary_source_types) >= 2
        rows.append({
            "construct": construct,
            "supported_for_explanation": "yes" if supported else "descriptive_only",
            "evidence_count": len(items),
            "primary_evidence_count": len(primary_items),
            "independent_documents": len(documents),
            "primary_documents": len(primary_documents),
            "source_types_count": len(source_types),
            "primary_source_types_count": len(primary_source_types),
            "source_types": "; ".join(source_types),
            "primary_source_types": "; ".join(primary_source_types),
            "claim": CONSTRUCT_CLAIMS.get(construct, ""),
            "evidence_rule": "supported by at least two independent primary documentary sources or by consistent evidence across different primary document types",
        })
    return rows


def design_rows(claims):
    rows = []
    for claim in claims:
        construct = claim["construct"]
        rows.append({
            "construct": construct,
            "supported_for_explanation": claim["supported_for_explanation"],
            "design_requirement": DESIGN_REQUIREMENTS.get(construct, ""),
            "empirical_basis": claim["claim"],
            "evidence_count": claim["evidence_count"],
            "primary_evidence_count": claim["primary_evidence_count"],
            "independent_documents": claim["independent_documents"],
            "primary_documents": claim["primary_documents"],
            "source_types": claim["source_types"],
            "primary_source_types": claim["primary_source_types"],
        })
    return rows


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_tables(connection, evidence, claims, designs):
    connection.executescript("""
        DROP TABLE IF EXISTS coded_evidence;
        DROP TABLE IF EXISTS construct_claims;
        DROP TABLE IF EXISTS design_requirements;
        CREATE TABLE coded_evidence (
            id INTEGER PRIMARY KEY,
            document TEXT NOT NULL,
            source_type TEXT NOT NULL,
            evidence_role TEXT NOT NULL,
            page INTEGER NOT NULL,
            sentence TEXT NOT NULL,
            code_id TEXT NOT NULL,
            code_label TEXT NOT NULL,
            code_type TEXT NOT NULL,
            construct TEXT NOT NULL,
            matched_terms TEXT NOT NULL
        );
        CREATE INDEX coded_evidence_code ON coded_evidence(code_id, construct);
        CREATE INDEX coded_evidence_document_page ON coded_evidence(document, page);
        CREATE TABLE construct_claims (
            construct TEXT PRIMARY KEY,
            supported_for_explanation TEXT NOT NULL,
            evidence_count INTEGER NOT NULL,
            primary_evidence_count INTEGER NOT NULL,
            independent_documents INTEGER NOT NULL,
            primary_documents INTEGER NOT NULL,
            source_types_count INTEGER NOT NULL,
            primary_source_types_count INTEGER NOT NULL,
            source_types TEXT NOT NULL,
            primary_source_types TEXT NOT NULL,
            claim TEXT NOT NULL,
            evidence_rule TEXT NOT NULL
        );
        CREATE TABLE design_requirements (
            construct TEXT PRIMARY KEY,
            supported_for_explanation TEXT NOT NULL,
            design_requirement TEXT NOT NULL,
            empirical_basis TEXT NOT NULL,
            evidence_count INTEGER NOT NULL,
            primary_evidence_count INTEGER NOT NULL,
            independent_documents INTEGER NOT NULL,
            primary_documents INTEGER NOT NULL,
            source_types TEXT NOT NULL,
            primary_source_types TEXT NOT NULL
        );
    """)
    connection.executemany(
        """
        INSERT INTO coded_evidence(
            document, source_type, evidence_role, page, sentence, code_id, code_label,
            code_type, construct, matched_terms
        ) VALUES (
            :document, :source_type, :evidence_role, :page, :sentence, :code_id, :code_label,
            :code_type, :construct, :matched_terms
        )
        """,
        evidence,
    )
    connection.executemany(
        """
        INSERT INTO construct_claims(
            construct, supported_for_explanation, evidence_count, primary_evidence_count,
            independent_documents, primary_documents, source_types_count, primary_source_types_count,
            source_types, primary_source_types, claim, evidence_rule
        ) VALUES (
            :construct, :supported_for_explanation, :evidence_count, :primary_evidence_count,
            :independent_documents, :primary_documents, :source_types_count, :primary_source_types_count,
            :source_types, :primary_source_types, :claim, :evidence_rule
        )
        """,
        claims,
    )
    connection.executemany(
        """
        INSERT INTO design_requirements(
            construct, supported_for_explanation, design_requirement,
            empirical_basis, evidence_count, primary_evidence_count, independent_documents,
            primary_documents, source_types, primary_source_types
        ) VALUES (
            :construct, :supported_for_explanation, :design_requirement,
            :empirical_basis, :evidence_count, :primary_evidence_count, :independent_documents,
            :primary_documents, :source_types, :primary_source_types
        )
        """,
        designs,
    )
    connection.commit()


def main():
    parser = argparse.ArgumentParser(description="Build qualitative coding evidence matrices")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--codes", type=Path, default=CODES_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    if not args.db.exists():
        parser.error("database does not exist: run build_index.py first")
    if not args.codes.exists():
        parser.error(f"codes file does not exist: {args.codes}")

    codes = load_codes(args.codes)
    source_overrides = load_source_types(SOURCE_TYPES_PATH)
    connection = sqlite3.connect(args.db)
    inventory = document_inventory(connection, source_overrides)
    evidence = code_evidence(connection, codes, source_overrides)
    claims = claim_rows(evidence)
    designs = design_rows(claims)
    write_tables(connection, evidence, claims, designs)
    connection.close()

    write_csv(
        args.output / "document_inventory.csv",
        inventory,
        ["document", "source_type", "evidence_role"],
    )
    write_csv(
        args.output / "evidence_matrix.csv",
        evidence,
        ["document", "source_type", "evidence_role", "page", "code_id", "code_label", "code_type", "construct", "matched_terms", "sentence"],
    )
    write_csv(
        args.output / "construct_claims.csv",
        claims,
        ["construct", "supported_for_explanation", "evidence_count", "primary_evidence_count", "independent_documents", "primary_documents", "source_types_count", "primary_source_types_count", "source_types", "primary_source_types", "claim", "evidence_rule"],
    )
    write_csv(
        args.output / "design_requirements.csv",
        designs,
        ["construct", "supported_for_explanation", "design_requirement", "empirical_basis", "evidence_count", "primary_evidence_count", "independent_documents", "primary_documents", "source_types", "primary_source_types"],
    )

    print(f"Documents inventoried: {len(inventory)}")
    print(f"Coded evidence rows: {len(evidence)}")
    print(f"Construct claims: {len(claims)}")
    print(f"Output folder: {args.output}")


if __name__ == "__main__":
    main()
