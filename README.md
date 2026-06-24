# PDF Search for Liana

Программа ищет слово или фразу в PDF-документах и показывает найденные
предложения, название документа и номер страницы.

## Windows

1. Установите [Python 3](https://www.python.org/downloads/) и
[Git for Windows](https://git-scm.com/download/win). При установке Python
отметьте `Add Python to PATH`.

2. Откройте PowerShell и выполните:

```powershell
git clone https://github.com/nurzhanova2/pdf_search_for_liana.git
cd pdf_search_for_liana
py -m pip install -r requirements.txt
```

3. Положите ZIP-архив с PDF в папку проекта и создайте базу:

```powershell
py build_index.py drive-download-20260622T060346Z-3-001.zip
```

4. Запустите сайт:

```powershell
py server.py
```

5. Откройте <http://127.0.0.1:8000> в браузере.

## macOS или Linux

```bash
git clone https://github.com/nurzhanova2/pdf_search_for_liana.git
cd pdf_search_for_liana
python3 -m pip install -r requirements.txt
python3 build_index.py drive-download-20260622T060346Z-3-001.zip
python3 server.py
```

Введите слово или фразу. На странице выводится по 20 результатов. Кнопка
скачивания сохраняет все найденные предложения в CSV. Для остановки сервера
нажмите `Control+C` в терминале.

Поиск без сайта:

```powershell
py search.py "personal data"
```

## Qualitative coding для исследования

После создания `pdf_search.db` запустите автоматическое первичное кодирование:

```bash
python3 qualitative_coding.py
```

На Windows:

```powershell
py qualitative_coding.py
```

Скрипт использует `codes.json` и строит traceable workflow:

- `analysis_output/document_inventory.csv` — список документов и тип источника;
- `analysis_output/evidence_matrix.csv` — фрагмент документа, страница, code, construct, matched terms;
- `analysis_output/construct_claims.csv` — проверка evidence rule: claim считается supported, если есть минимум 2 независимых документа или разные типы источников;
- `analysis_output/design_requirements.csv` — перевод evidence-based claims в design requirements для network governance framework.

Типы источников уже размечены в `source_types.json`. Evidence rule считается по `primary_documentary` источникам: `law`, `strategy`, `regulation`, `institutional_protocol`, `government_guidance`, `government_communication`, `institutional_report`. `international_report` и `institutional_interview` используются для triangulation, а `academic_literature`, `news_media`, `expert_commentary`, `interview_transcript` остаются contextual material и не являются единственным основанием для explanatory claims.

В веб-интерфейсе блок `Qualitative coding` показывает construct-level claims, coded evidence по 20 строк на страницу и дает скачать `coded_evidence.csv` с выбранными фильтрами.


## Итоги coded analysis

После последнего запуска `qualitative_coding.py` получены такие результаты:

- всего документов в базе: 40;
- primary documentary sources: 10;
- triangulation sources: 5;
- contextual literature sources: 25;
- всего coded evidence rows: 15,206;
- primary documentary coded rows: 5,315;
- triangulation coded rows: 2,404;
- contextual coded rows: 7,487.

Construct-level claims поддержаны primary documentary evidence:

| Construct | Total excerpts | Primary excerpts | Primary documents |
| --- | ---: | ---: | ---: |
| CSG outcomes | 4,596 | 1,314 | 10 |
| Dynamic capabilities | 3,409 | 1,339 | 10 |
| Institutional fragmentation | 2,772 | 704 | 10 |
| Coordination mechanisms | 1,977 | 1,070 | 9 |
| Cooperation incentives and constraints | 1,732 | 740 | 9 |
| Governance failure modes | 720 | 148 | 9 |

Главный вывод для conclusion: coded evidence показывает, что reactive cybersecurity governance в Казахстане связано не только с технологиями или финансированием, а с повторяющимися governance patterns: institutional fragmentation, cooperation constraints, uneven coordination mechanisms, role ambiguity, weak escalation paths и слабым follow-through.

Важно: автоматическое кодирование — это первый проход для evidence management. Для финального текста нужно вручную проверить релевантные excerpts, особенно inductive codes и single-source claims.

