#!/usr/bin/env python3
import csv
import io
import json
import re
import sqlite3
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "pdf_search.db"
PDF_DIR = HERE / "pdfs"
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-ZА-ЯЁ0-9])")


@lru_cache(maxsize=32)
def search(query):
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    connection = sqlite3.connect(DB_PATH)
    rows = connection.execute(
        "SELECT document, page, text FROM pages WHERE instr(lower(text), lower(?)) > 0 "
        "ORDER BY document COLLATE NOCASE, page",
        (query,),
    )
    results = []
    for document, page, text in rows:
        for sentence in SENTENCE.split(text):
            if pattern.search(sentence):
                results.append({"document": document, "page": page, "sentence": sentence})
    connection.close()
    return tuple(results)


def coded_evidence(code="", construct="", page=1):
    per_page = 20
    connection = sqlite3.connect(DB_PATH)
    has_table = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='coded_evidence'"
    ).fetchone()
    if not has_table:
        connection.close()
        return {"ready": False, "page": page, "per_page": per_page, "total": 0, "results": []}

    filters = []
    values = []
    if code:
        filters.append("code_id = ?")
        values.append(code)
    if construct:
        filters.append("construct = ?")
        values.append(construct)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    total = connection.execute(f"SELECT count(*) FROM coded_evidence {where}", values).fetchone()[0]
    offset = (page - 1) * per_page
    rows = connection.execute(
        f"""
        SELECT document, source_type, evidence_role, page, sentence, code_id, code_label,
               code_type, construct, matched_terms
        FROM coded_evidence
        {where}
        ORDER BY construct, code_id, document COLLATE NOCASE, page
        LIMIT ? OFFSET ?
        """,
        [*values, per_page, offset],
    )
    results = [
        {
            "document": document,
            "source_type": source_type,
            "evidence_role": evidence_role,
            "page": page_number,
            "sentence": sentence,
            "code_id": code_id,
            "code_label": code_label,
            "code_type": code_type,
            "construct": construct_name,
            "matched_terms": matched_terms,
        }
        for document, source_type, evidence_role, page_number, sentence, code_id, code_label,
        code_type, construct_name, matched_terms in rows
    ]
    connection.close()
    return {"ready": True, "page": page, "per_page": per_page, "total": total, "results": results}


def coding_summary():
    connection = sqlite3.connect(DB_PATH)
    has_table = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='construct_claims'"
    ).fetchone()
    if not has_table:
        connection.close()
        return {"ready": False, "claims": []}
    rows = connection.execute(
        """
        SELECT construct, supported_for_explanation, evidence_count,
               primary_evidence_count, independent_documents, primary_documents,
               source_types, primary_source_types, claim
        FROM construct_claims
        ORDER BY construct
        """
    )
    claims = [
        {
            "construct": construct,
            "supported_for_explanation": supported,
            "evidence_count": evidence_count,
            "primary_evidence_count": primary_evidence_count,
            "independent_documents": independent_documents,
            "primary_documents": primary_documents,
            "source_types": source_types,
            "primary_source_types": primary_source_types,
            "claim": claim,
        }
        for construct, supported, evidence_count, primary_evidence_count, independent_documents,
        primary_documents, source_types, primary_source_types, claim in rows
    ]
    connection.close()
    return {"ready": True, "claims": claims}


def export_coded_evidence(code="", construct=""):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Документ", "Тип источника", "Роль источника", "Страница", "Код", "Название кода",
        "Тип кода", "Конструкт", "Совпавшие термины", "Фрагмент",
    ])
    connection = sqlite3.connect(DB_PATH)
    has_table = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='coded_evidence'"
    ).fetchone()
    if has_table:
        filters = []
        values = []
        if code:
            filters.append("code_id = ?")
            values.append(code)
        if construct:
            filters.append("construct = ?")
            values.append(construct)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        rows = connection.execute(
            f"""
            SELECT document, source_type, evidence_role, page, code_id, code_label,
                   code_type, construct, matched_terms, sentence
            FROM coded_evidence
            {where}
            ORDER BY construct, code_id, document COLLATE NOCASE, page
            """,
            values,
        )
        writer.writerows(rows)
    connection.close()
    return ("\ufeff" + output.getvalue()).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, body, content_type, status=200, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_bytes((HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0].strip()
            try:
                page = max(1, int(params.get("page", ["1"])[0]))
            except ValueError:
                page = 1
            all_results = search(query) if query else []
            per_page = 20
            start = (page - 1) * per_page
            data = {
                "query": query,
                "page": page,
                "per_page": per_page,
                "total": len(all_results),
                "results": all_results[start:start + per_page],
            }
            self.send_bytes(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")
            return
        if parsed.path == "/api/coding/summary":
            data = coding_summary()
            self.send_bytes(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")
            return
        if parsed.path == "/api/coding/evidence":
            params = parse_qs(parsed.query)
            try:
                page = max(1, int(params.get("page", ["1"])[0]))
            except ValueError:
                page = 1
            data = coded_evidence(
                code=params.get("code", [""])[0].strip(),
                construct=params.get("construct", [""])[0].strip(),
                page=page,
            )
            self.send_bytes(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")
            return
        if parsed.path == "/api/coding/export":
            params = parse_qs(parsed.query)
            body = export_coded_evidence(
                code=params.get("code", [""])[0].strip(),
                construct=params.get("construct", [""])[0].strip(),
            )
            self.send_bytes(
                body,
                "text/csv; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="coded_evidence.csv"'},
            )
            return
        if parsed.path == "/api/export":
            query = parse_qs(parsed.query).get("q", [""])[0].strip()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Запрос", "Документ", "Страница", "Предложение"])
            for result in search(query) if query else []:
                writer.writerow([
                    query,
                    result["document"],
                    result["page"],
                    result["sentence"],
                ])
            body = ("\ufeff" + output.getvalue()).encode("utf-8")
            self.send_bytes(
                body,
                "text/csv; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="mentions.csv"'},
            )
            return
        if parsed.path.startswith("/pdf/"):
            name = Path(unquote(parsed.path.removeprefix("/pdf/"))).name
            path = PDF_DIR / name
            if path.is_file():
                self.send_bytes(path.read_bytes(), "application/pdf")
                return
        self.send_bytes(b"Not found", "text/plain", 404)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    if not DB_PATH.exists():
        raise SystemExit("Run build_index.py first")
    print("Open http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
