"""Entry point: `streamlit run app.py`."""

from __future__ import annotations

import logging

import streamlit as st

from ui.common import get_settings, language_selector, require_user

st.set_page_config(page_title="Invoice Data Extractor", page_icon="🧾", layout="wide")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

strings = language_selector()
st.session_state["owner"] = require_user(strings, get_settings())

page = st.navigation(
    [
        st.Page("ui/extract_page.py", title=strings["nav_extract"], icon=":material/document_scanner:", default=True),
        st.Page("ui/history_page.py", title=strings["nav_history"], icon=":material/history:", url_path="history"),
    ]
)
page.run()
