import streamlit as st
import pandas as pd
import sqlite3
from database import get_crono, get_data_analysis
from frontend import translations
import logging
import os

# Configurazione della pagina
st.set_page_config(page_title="Cronologia Analisi", layout="wide")


#andiamo a caricare i nostri file temporanei in una cartella specifica
temp_files_dir = "temp_files"
os.makedirs(temp_files_dir, exist_ok=True)

with st.sidebar:
    # Creiamo due colonne nel sidebar per allineare Logo+Titolo e Selectbox
    col1, col2 = st.columns(2, vertical_alignment="top")
    with st.form(key="login_form"):
        with col1:
            st.logo("https://www.oaks.cloud/_next/static/media/oaks.1ea4e367.svg",    #inseriamo il logo dell'azienda nella nostra app
                size="large",
                link="https://www.oaks.cloud/")
            ""
            st.title(f":house:**Homepage**")
    with st.form(key="language_form"):
        with col2:
            lang = st.selectbox("A", ["IT", "EN", "ES"], label_visibility="hidden")
            # selezioniamo il dizionario della lingua corrente in base alla selezione dell'utente
            current_lang = translations[lang]
            st.session_state.translations = translations
            
#qua andiamo a gestire il login dell'utente, usando il nostro secrets.toml per 
#eseguire accesso tramite Microsoft Azure Entra
if not st.experimental_user.is_logged_in:
    st.title("Microsoft Login:streamlit:")
    st.subheader(f":material/Login: {current_lang['login_prompt']}")
    logging.info("Launched app, waiting for the User Login.")

    if st.button(current_lang["login_button"]):
        st.login()

else:
    with st.sidebar:
        if st.experimental_user.is_logged_in:
            st.markdown(current_lang["greeting"].format(name=st.experimental_user.name, email=st.experimental_user.email))
            logging.info(f"User {st.experimental_user.name} ({st.experimental_user.email}) successfully logged in.")

        if st.button(current_lang["logout_button"]):
            st.logout()

    # Connessione al database
    conn = sqlite3.connect('cronologia.db')
    cursor = conn.cursor()

    # Recupero della cronologia delle analisi
    view_analysis = get_crono(cursor)

    # Titolo della pagina
    st.title("🧾 Cronologia delle Analisi")

    #andiamo a mostrare la cronologia delle analisi effettuate mediante vari bottoni, se non è vuota
    #allora mostriamo la cronologia, altrimenti mostriamo un messaggio di errore
    view_analysis = get_crono(cursor)
    view_analysis_names = [f"{get_analysis[1]} - {get_analysis[2]}" for get_analysis in view_analysis]
    st.header(f":bookmark_tabs: **{current_lang['analysis_history']}**")

    if 'history_selection' not in st.session_state:
        st.session_state.history_selection = None

    #quando l'utente seleziona un'analisi dalla cronologia, recupera il blob salvato nel database
    #e lo salva in un file temporaneo, in modo tale da poterlo usare.
    for i, analysis_item in enumerate(view_analysis_names):
        if st.button(analysis_item, key=f"history_btn_{i}"):
        #andiamo a creare una chiave di sessione per la cronologia, in modo tale da non sovrascrivere
        #le analisi precedenti, e andiamo a verificare se la chiave è presente nella sessione
            st.session_state.history_selection = analysis_item
            
            id_get_analysis = view_analysis[i][0]
            history_session_key = f"history_{id_get_analysis}"
            
            if history_session_key not in st.session_state:
                st.session_state[history_session_key] = {}
            
            if "all_history" not in st.session_state or st.session_state["all_history"] != id_get_analysis:
                st.session_state["all_history"] = id_get_analysis
                st.session_state['extracted_data'] = get_data_analysis(cursor, id_get_analysis)
                st.session_state['selected_analysis_name'] = analysis_item
                
               #qua andiamo a creare un file temporaneo per il blob salvato nel database
                temp_file_path = os.path.join(temp_files_dir, f"temp_{id_get_analysis}.pdf")
                st.session_state[history_session_key]['temporary_file_path'] = temp_file_path

                try:
                    blob_data = st.session_state['extracted_data'].get("file_blob")
                    if blob_data:
                        with open(temp_file_path, "wb") as temp_file:
                            temp_file.write(blob_data)
                        logging.info(f"Temporary file {temp_file_path} recreated successfully.")
                    else:
                        logging.warning("Blob data not found in the extracted data.")
                        st.error(current_lang["data_not_found"])
                except Exception as e:
                    logging.error(f"Error recreating temporary file: {e}")
                    st.error(current_lang["rectangle_error"].format(error=e))

                st.session_state['analysis_source'] = 'history'
                st.rerun()

    if st.session_state.history_selection:
        st.info(f"Selezionato: {st.session_state.history_selection}")