# pdf_search_for_liana-

The SQLite database contains the text of every PDF page. Search results show each
matching sentence, its document, and page number.

Build or rebuild the database:

```bash
python3 pdf_search/build_index.py drive-download-20260622T060346Z-3-001.zip
```

Search for a word or phrase (the search is case-insensitive):

```bash
python3 pdf_search/search.py cybersecurity
python3 pdf_search/search.py "personal data"
```

Or start the browser interface:

```bash
python3 pdf_search/server.py
```

Then open <http://127.0.0.1:8000>. Click a result heading to open the source PDF
at the matching page. The CSV download button exports every matching sentence
with its document and page number.
