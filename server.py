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


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, body, content_type, status=200, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

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
