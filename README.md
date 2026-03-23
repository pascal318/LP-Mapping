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

- The app uses fixed source paths for v1, but the parser layer is adapter-based so more sources can be added later.
- Investor matching uses exact, normalized exact, and fuzzy matching (`rapidfuzz.WRatio`) with a minimum score of `70`.
- Results show deduped LPs and keep unmatched investors visible for each company.
