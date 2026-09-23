"""Page 2: browse, search, reopen and clear past analyses."""

from __future__ import annotations

import logging
from datetime import datetime

import streamlit as st

from ui.common import get_settings, get_store, render_result, strings

log = logging.getLogger(__name__)

s = strings()
store = get_store()
owner = st.session_state["owner"]

st.title(f"🗂️ {s['history_title']}")
st.caption(s["history_caption"].format(limit=get_settings().history_limit))


@st.dialog(" ", width="large")
def open_analysis(analysis_id: int, file_name: str) -> None:
    record = store.get(owner, analysis_id)
    if record is None:
        st.error(s["missing_analysis"])
        return
    data, pdf = record
    st.subheader(file_name)
    render_result(f"hist_{analysis_id}", file_name, pdf, data, s)


@st.dialog(" ")
def confirm_clear() -> None:
    st.warning(s["clear_confirm"])
    yes, no = st.columns(2)
    if yes.button(s["clear_yes"], type="primary", width="stretch"):
        store.clear(owner)
        st.session_state["history_cleared"] = True
        st.rerun()
    if no.button(s["cancel"], width="stretch"):
        st.rerun()


if st.session_state.pop("history_cleared", False):
    st.toast(s["cleared"], icon="🗑️")

search_col, clear_col = st.columns([4, 1], vertical_alignment="bottom")
search = search_col.text_input(s["search_placeholder"], placeholder=s["search_placeholder"],
                               label_visibility="collapsed", icon=":material/search:")

try:
    rows = store.list(owner, search.strip())
except Exception:
    log.exception("Could not read history")
    rows = []
    st.error("The history database could not be read.")

if clear_col.button(s["clear_history"], icon=":material/delete:", width="stretch", disabled=not rows):
    confirm_clear()

if not rows:
    st.info(s["history_empty"])

with st.container(border=True):
    for row in rows:
        name_col, date_col, open_col = st.columns([4, 2, 1], vertical_alignment="center")
        name_col.markdown(f"**{row['file_name']}**")
        created = datetime.fromisoformat(row["created_at"]).strftime("%d %b %Y, %H:%M")
        date_col.caption(f"📅 {created}")
        if open_col.button(s["open"], key=f"open_{row['id']}", width="stretch"):
            open_analysis(row["id"], row["file_name"])
