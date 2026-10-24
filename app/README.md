# Emerging Artist Exposure dashboard

From the project root, install and launch with Python 3.10 or newer:

```powershell
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe -m streamlit run app/streamlit_app.py --server.address=127.0.0.1 --server.port=8501
```

Open http://127.0.0.1:8501. The four tabs cover the shortlist, artist and entry-track detail, listener segments, and data notes. Select an artist from the ranked table or scatter, then open Artist Detail. The download includes the full filtered shortlist with raw metric values.

The app reads only the six existing aggregate tables through `analysis.store`. It never reads or processes raw listens. Without `EAE_DATA_DIR`, it uses `data/aggregates` if a manifest exists, otherwise `data/demo/aggregates`. Set `EAE_DATA_DIR` to explicitly choose another aggregate folder; relative paths resolve from the project root. An explicit folder without a manifest produces an error. Synthetic data always shows a warning.

Run checks from the project root:

```powershell
.venv/Scripts/python.exe -m pytest -q
```

Dashboard acceptance tests cover demo rankings for both populations, filters, zero weights and reset, empty results, selection handlers, entry tracks, weekly audience, segment return, CSV schema and precision, missing folders, manifest build time and quality banners. The non-demo manifest test uses a temporary copy of the demo aggregates; real-dataset row-count validation requires already-built real aggregates and their cleaning summary.

Manual browser verification: click a table row or scatter point, open Artist Detail, check the selected artist, and download the CSV. This remains a manual check when no browser is connected to the automation tools.
