"""Shared UI pieces: settings, language, login, and the result editor."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from invoice_extractor.annotate import annotated_png
from invoice_extractor.config import Settings, load_settings
from invoice_extractor.export import build_export, to_json_bytes
from invoice_extractor.i18n import DEFAULT_LANGUAGE, LANGUAGES, t
from invoice_extractor.parsing import HEADER_FIELDS, ITEM_COLUMNS
from invoice_extractor.storage import HistoryStore

log = logging.getLogger(__name__)
DEMO_OWNER = "local"


# --------------------------------------------------------------------------- resources
@st.cache_resource
def get_settings() -> Settings:
    return load_settings()


@st.cache_resource
def get_store() -> HistoryStore:
    s = get_settings()
    return HistoryStore(s.db_path, s.history_limit)


def strings() -> dict:
    return t(st.session_state.get("language", DEFAULT_LANGUAGE))


# --------------------------------------------------------------------------- sidebar
def language_selector() -> dict:
    st.session_state.setdefault("language", DEFAULT_LANGUAGE)
    st.sidebar.selectbox(
        "🌐 Language",
        LANGUAGES,
        key="language",
        format_func=lambda code: {"EN": "English", "IT": "Italiano", "ES": "Español"}[code],
    )
    return strings()


# --------------------------------------------------------------------------- auth
def auth_configured() -> bool:
    """Microsoft Entra ID login is enabled only when [auth] exists in secrets.toml."""
    try:
        return "auth" in st.secrets
    except Exception:  # no secrets.toml at all
        return False


def require_user(s: dict, settings: Settings) -> str:
    """Return the history owner id, or stop the script and show the login screen."""
    if not auth_configured():
        return DEMO_OWNER

    if not st.user.is_logged_in:
        st.title(s["title"])
        st.info(s["login_prompt"])
        if st.button(s["login_button"], type="primary", icon=":material/login:"):
            st.login()
        st.stop()

    email = (st.user.get("email") or "").lower()
    if settings.allowed_emails and email not in settings.allowed_emails:
        log.warning("Rejected login for %s", email)
        st.error(s["not_authorized"].format(email=email))
        st.button(s["logout_button"], on_click=st.logout)
        st.stop()

    with st.sidebar:
        st.markdown(s["greeting"].format(name=st.user.get("name") or email))
        st.button(s["logout_button"], on_click=st.logout, icon=":material/logout:")
    return email


# --------------------------------------------------------------------------- result editor
@st.cache_data(show_spinner=False, max_entries=32)
def _annotated(pdf: bytes, boxes_json: str, page_json: str) -> bytes:
    return annotated_png(pdf, json.loads(boxes_json), json.loads(page_json))


def _items_frame(items: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(items, columns=ITEM_COLUMNS)


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.astype(object).where(df.notna(), None)
    return [row for row in clean.to_dict("records") if any(v not in (None, "") for v in row.values())]


def render_result(key: str, file_name: str, pdf: bytes, data: dict[str, Any], s: dict) -> None:
    """Editable fields next to the highlighted document, line items and download below."""
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.subheader(s["vendor_info"])
        fields = {
            name: st.text_input(s["fields"][name], value=data["fields"].get(name, ""), key=f"{key}_{name}")
            for name in HEADER_FIELDS
        }
        cat_idx = st.selectbox(
            s["category_label"],
            options=range(len(s["categories"])),  # store the index so switching language keeps the choice
            format_func=lambda i: s["categories"][i],
            index=None,
            key=f"{key}_category",
        )
        category = s["categories"][cat_idx] if cat_idx is not None else None

    with right:
        st.subheader(s["highlighted"])
        try:
            png = _annotated(pdf, json.dumps(data.get("boxes", {})), json.dumps(data.get("page", {})))
            st.image(png, width="stretch")
        except Exception:
            log.exception("Could not render preview for %s", file_name)
            st.warning(s["image_error"])

    st.subheader(s["items_header"])
    cols = s["columns"]
    edited = st.data_editor(
        _items_frame(data.get("items", [])),
        key=f"{key}_items",
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "description": st.column_config.TextColumn(cols["description"], width="medium"),
            "product_code": st.column_config.TextColumn(cols["product_code"]),
            "quantity": st.column_config.NumberColumn(cols["quantity"], min_value=0, format="%.2f"),
            "unit_price": st.column_config.NumberColumn(cols["unit_price"], format="%.2f"),
            "amount": st.column_config.NumberColumn(cols["amount"], format="%.2f"),
        },
    )

    export = build_export(fields, _records(edited), category, s)
    st.download_button(
        s["download_json"],
        data=to_json_bytes(export),
        file_name=f"{Path(file_name).stem}.json",
        mime="application/json",
        type="primary",
        icon=":material/download:",
        key=f"{key}_download",
    )
