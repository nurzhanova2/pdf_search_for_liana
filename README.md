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
