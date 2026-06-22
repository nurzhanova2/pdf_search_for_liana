#!/usr/bin/env python3
import argparse
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "pdf_search.db"
SENTENCE = re.compile(r"(?<!\b[A-ZА-ЯЁ])(?<=[.!?])\s+(?=[A-ZА-ЯЁ0-9])")


def matching_sentences(text, query):
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    for sentence in SENTENCE.split(text):
        if pattern.search(sentence):
            yield pattern.sub(lambda m: f"\033[1;31m{m.group(0)}\033[0m", sentence.strip())


def main():
    parser = argparse.ArgumentParser(
        description="Find all sentences containing a word or phrase"
    )
    parser.add_argument("query", nargs="+", help="word or phrase to find")
    args = parser.parse_args()
    query = " ".join(args.query).strip()
    if not DB_PATH.exists():
        parser.error(f"database does not exist: run build_index.py first")

    connection = sqlite3.connect(DB_PATH)
    rows = connection.execute(
        "SELECT document, page, text FROM pages WHERE instr(lower(text), lower(?)) > 0 "
        "ORDER BY document COLLATE NOCASE, page",
        (query,),
    )
    count = 0
    for document, page, text in rows:
        for sentence in matching_sentences(text, query):
            count += 1
            print(f"\n[{document}, page {page}]\n{sentence}")
    print(f"\nFound sentences: {count}")
    connection.close()


if __name__ == "__main__":
    main()
