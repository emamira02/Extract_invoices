"""Page 1: upload documents, analyse them, edit and download the results."""

from __future__ import annotations

import hashlib
import logging

import streamlit as st

from invoice_extractor.azure_client import AnalysisError
from invoice_extractor.files import InvalidFileError
from invoice_extractor.parsing import NoDocumentFound
from invoice_extractor.pipeline import load_sample, process_upload
from ui.common import get_settings, get_store, render_result, strings

log = logging.getLogger(__name__)

s = strings()
settings = get_settings()
store = get_store()
owner = st.session_state["owner"]
results: dict = st.session_state.setdefault("results", {})
# Failed files are remembered so a rerun (any widget change) does not call Azure again.
failures: dict = st.session_state.setdefault("failures", {})

st.title(f"🧾 {s['title']}")
st.markdown(f"{s['subtitle']}  \n{s['how_it_works']}")

demo = not settings.azure_configured
if demo:
    st.info(s["demo_banner"], icon=":material/science:")


def _add_result(file_id: str, name: str, pdf: bytes, data: dict) -> None:
    try:
        store.add(owner, name, data, pdf)
    except Exception:  # history is a convenience: never block the result on it
        log.exception("Could not save %s to history", name)
    results[file_id] = {"name": name, "pdf": pdf, "data": data}


# --------------------------------------------------------------------------- input
upload_col, actions_col = st.columns([3, 1], vertical_alignment="bottom")
with upload_col:
    uploads = st.file_uploader(
        s["upload_label"],
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        disabled=demo,
        key=f"uploader_{st.session_state.get('uploader_gen', 0)}",
        help=s["demo_upload_disabled"] if demo else None,
    )
with actions_col:
    if st.button(s["try_sample"], icon=":material/description:", width="stretch",
                 type="primary" if demo else "secondary"):
        if "sample" not in results:
            name, pdf, data = load_sample()
            _add_result("sample", name, pdf, data)
            st.rerun()
    if st.button(s["clear_uploads"], icon=":material/delete_sweep:", width="stretch", disabled=not (results or failures)):
        results.clear()
        failures.clear()
        st.session_state["uploader_gen"] = st.session_state.get("uploader_gen", 0) + 1
        st.rerun()

if demo:
    st.caption(s["demo_upload_disabled"])

# --------------------------------------------------------------------------- analysis
for upload in uploads or []:
    content = upload.getvalue()
    file_id = hashlib.sha256(content).hexdigest()[:16]
    if file_id in results:
        continue
    if file_id in failures:
        level, message = failures[file_id]
        getattr(st, level)(message)
        continue
    with st.spinner(s["analyzing"].format(file_name=upload.name)):
        try:
            pdf, data = process_upload(upload.name, content, settings)
        except InvalidFileError as exc:
            failures[file_id] = ("warning", s["invalid_file"].format(file_name=upload.name, error=exc))
        except (AnalysisError, NoDocumentFound) as exc:
            log.warning("Analysis failed for %s: %s", upload.name, exc)
            failures[file_id] = ("error", s["analysis_failed"].format(file_name=upload.name, error=exc))
        except Exception as exc:  # unexpected: log the traceback, show a short message
            log.exception("Unexpected error while analysing %s", upload.name)
            failures[file_id] = ("error", s["analysis_failed"].format(file_name=upload.name, error=type(exc).__name__))
    if file_id in failures:
        level, message = failures[file_id]
        getattr(st, level)(message)
        continue
    _add_result(file_id, upload.name, pdf, data)
    st.toast(s["analysis_success"].format(file_name=upload.name), icon="✅")

# --------------------------------------------------------------------------- results
for i, (file_id, res) in enumerate(results.items()):
    with st.expander(f"**{res['name']}**", expanded=(i == 0)):
        render_result(f"res_{file_id}", res["name"], res["pdf"], res["data"], s)
