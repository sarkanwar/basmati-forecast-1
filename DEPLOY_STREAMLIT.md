
# Deploy to Streamlit Cloud

1. Push this repo to GitHub.
2. On https://share.streamlit.io, click **New app** and connect your repo.
3. **Main file path:** `streamlit_app.py`
4. **Python version:** 3.10 or 3.11
5. The app will build using `requirements.txt` and launch.

If you see import errors, ensure the repo contains this structure:

```
basmati-forecast/
  basmati/               # package
  streamlit_app.py       # entry point
  cli.py
  requirements.txt
  README.md
```

Run locally:
```
pip install -r requirements.txt
streamlit run streamlit_app.py
```
