# LP Look-Through Lookup Tool

Local Streamlit app for mapping company investors to LP look-through exposure using:

- `/Users/pascalsuhrcke/Downloads/Atrea_LP_Database_Export.xlsx`
- `/Users/pascalsuhrcke/Downloads/Company Look-Up.xlsx`

## Run

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Start the app:

```bash
python3 -m streamlit run app.py
```

Run tests:

```bash
pytest
```

## Notes

- On your local machine, the app can read the fixed files in `Downloads`.
- In deployed environments such as Railway, upload both workbooks in the UI to build a lookup session.
- The parser layer is adapter-based so more sources can be added later.
- Investor matching uses exact, normalized exact, and fuzzy matching (`rapidfuzz.WRatio`) with a minimum score of `70`.
- Results show deduped LPs and keep unmatched investors visible for each company.
