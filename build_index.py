#!/usr/bin/env python3
import argparse
import base64
import re
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PDF_DIR = HERE / "pdfs"
DB_PATH = HERE / "pdf_search.db"
EXTRACTOR = HERE / "extract_pdf"


def compile_extractor():
    source = HERE / "extract_pdf.m"
    subprocess.run(
        [
            "clang",
            "-fobjc-arc",
            "-framework",
            "Foundation",
            "-framework",
            "PDFKit",
            str(source),
            "-o",
            str(EXTRACTOR),
        ],
        check=True,
    )


def extract_archive(archive):
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        for item in zf.infolist():
            if item.is_dir() or not item.filename.lower().endswith(".pdf"):
                continue
            name = Path(item.filename).name
            target = PDF_DIR / name
            with zf.open(item) as src, target.open("wb") as dst:
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)


def pages_from_pdf(path):
    result = subprocess.run(
        [str(EXTRACTOR), str(path)], capture_output=True, text=True, check=True
    )
    for line in result.stdout.splitlines():
        page, encoded = line.split("\t", 1)
        yield int(page), base64.b64decode(encoded).decode("utf-8")


def normalize(text):
    text = text.replace("\u00ad", "").replace("\r", "\n")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def main():
    parser = argparse.ArgumentParser(description="Build a searchable PDF page database")
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    if not args.archive.is_file():
        parser.error(f"archive not found: {args.archive}")

    print("Extracting PDFs...")
    extract_archive(args.archive)
    print("Compiling PDF text extractor...")
    compile_extractor()

    pdfs = sorted(PDF_DIR.glob("*.pdf"), key=lambda p: p.name.casefold())
    connection = sqlite3.connect(DB_PATH)
    connection.executescript("""
        DROP TABLE IF EXISTS pages;
        CREATE TABLE pages (
            id INTEGER PRIMARY KEY,
            document TEXT NOT NULL,
            page INTEGER NOT NULL,
            text TEXT NOT NULL,
            UNIQUE(document, page)
        );
        CREATE INDEX pages_document_page ON pages(document, page);
    """)

    empty_pages = 0
    for number, pdf in enumerate(pdfs, 1):
        print(f"[{number:02d}/{len(pdfs)}] {pdf.name}", flush=True)
        try:
            rows = []
            for page, text in pages_from_pdf(pdf):
                clean = normalize(text)
                empty_pages += not bool(clean)
                rows.append((pdf.name, page, clean))
            connection.executemany(
                "INSERT INTO pages(document, page, text) VALUES (?, ?, ?)", rows
            )
            connection.commit()
        except (subprocess.CalledProcessError, ValueError) as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)

    total_pages, total_chars = connection.execute(
        "SELECT count(*), coalesce(sum(length(text)), 0) FROM pages"
    ).fetchone()
    connection.close()
    print(f"Done: {len(pdfs)} documents, {total_pages} pages, {total_chars} characters")
    if empty_pages:
        print(f"Warning: {empty_pages} pages have no text layer (OCR may be needed)")
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    main()
