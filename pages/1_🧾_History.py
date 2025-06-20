import streamlit as st
import os
import datetime
import pandas as pd
import logging
from backend.database import *
from frontend import translations, edit_data, delete_temp_file, show_navigation
from streamlit_searchbox import st_searchbox

#settiamo la lingua in italiano di default se non è già presente nella sessione
if 'language' not in st.session_state:
    st.session_state['language'] = 'IT'

st.session_state['current_page'] = 'history'

with st.sidebar:
    # Creiamo due colonne nel sidebar per allineare Logo+Titolo e Selectbox
    col1, col2 = st.columns(2, vertical_alignment="top")
    with col1:
        st.logo("https://www.oaks.cloud/_next/static/media/oaks.1ea4e367.svg",    
            size="large",
            link="https://www.oaks.cloud/")
        ""
        st.title(f":globe_with_meridians:**Dashboard**")
    with col2:
        lang = st.selectbox(
            "A", 
            ["IT", "EN", "ES"], 
            label_visibility="hidden",
            key="history_lang_selector",
            index=["IT", "EN", "ES"].index(st.session_state['language']), 
            on_change=lambda: st.session_state.update(language=st.session_state.history_lang_selector)
        )

        #andiamo a gestire il cambio della lingua in base alla selezione dell'utente
        if lang != st.session_state['language']:
            st.session_state['language'] = lang

        # selezioniamo il dizionario della lingua corrente in base alla selezione dell'utente
        current_lang = translations[st.session_state['language']]
        st.session_state.translations = translations

#qua andiamo a gestire il login dell'utente, usando il nostro secrets.toml per 
#eseguire accesso tramite Microsoft Azure Entra
if not st.user.is_logged_in:
    st.title("Microsoft Login:streamlit:")
    st.subheader(f":material/Login: {current_lang['login_prompt']}")
    logging.info("Launched app, waiting for the User Login.")

    if st.button(current_lang["login_button"]):
        st.login()

else:
    with st.sidebar:
        if st.user.is_logged_in:
            st.markdown(current_lang["greeting"].format(name=st.user.name, email=st.user.email))
            logging.info(f"User {st.user.name} ({st.user.email}) successfully logged in.")

        if st.button(current_lang["logout_button"], key="history_logout_btn"):
            st.logout()
        st.markdown("---")
        st.markdown("")
            
        show_navigation(page_prefix="history")

    #usiamo la temp_files_dir present nel session_state per salvare i file temporanei
    if 'temp_files_dir' in st.session_state:
        temp_files_dir = st.session_state.temp_files_dir
    else:
        temp_files_dir = "temp_files"
        os.makedirs(temp_files_dir, exist_ok=True)

    col1,col3 = st.columns([4.3,1])
    with col1:
        st.title(f"📋 {current_lang.get('analysis_history', 'Analysis History')}")

    with col3:
        #usiamo il decoratore @st.dialog per creare un popup che ci permetta di visualizzare il messaggio di avviso
        #e di confermare l'azione di cancellazione della cronologia
        @st.dialog(title=current_lang.get("clear_history", "Clear History"))
        #definiamo una funzione per confermare la cancellazione della cronologia, mediante un pulsante cancelliamo l'intera cronologia presente
        #nel database, chiedendo conferma all'utente prima di procedere
        #e mostrando un messaggio di successo o errore a seconda dell'esito dell'operazione
        def confirm_clear_history():
            st.warning(current_lang.get("clear_warning", "Are you sure? This action cannot be undone."))
            col1, col2 = st.columns(2)
            with col1:
                if st.button(current_lang.get("confirm_clear_history", "Yes, Clear History"), key="confirm_clear"):
                    try:
                        with st.spinner(current_lang.get("clearing", "Clearing history...")):
                            for file in os.listdir(temp_files_dir):
                                os.remove(os.path.join(temp_files_dir, file))
                            clear_db_history()
                            st.success(current_lang.get("clear_success", "History cleared successfully!"))
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            with col2:
                if st.button(current_lang.get("cancel_clear_history", "Cancel"), key="cancel_clear"):
                    st.rerun()

    search_col, clear_button_col = st.columns([4, 1])
    
    with search_col:
        #andiamo a definire una funzione per cercare le analisi in base alla query di ricerca
        #e a restituire soltanto i nomi delle analisi che corrispondono alla query di ricerca
        def search_analysis(search_term):
            all_analysis = get_crono()
            results = []
            if search_term:
                for analysis in all_analysis:
                    if search_term.lower() in analysis[1].lower():
                        results.append(analysis[1])
            return results
        #andiamo a creare una barra di ricerca per filtrare le analisi in base alla query di ricerca
        search_query = st_searchbox(
            search_function=search_analysis,
            key="history_search"
        )
    
    with clear_button_col:
        if st.button(current_lang.get("clear_history", "🗑️ Clear All History")):
            confirm_clear_history()

    #andiamo a definire una funzione per filtrare le analisi in base alla query di ricerca
        #e a restituire tutte le analisi se la query è vuota
        #in questo modo possiamo visualizzare solo le analisi che corrispondono alla query di ricerca
    def filter_analyses():
        all_analysis = get_crono()
        if search_query:
            return [analysis for analysis in all_analysis if search_query.lower() in analysis[1].lower()]
        return all_analysis

    container = st.container(border=True)
    cols = st.columns([0.0001, 0.95, 0.23])
    with cols[1]:
        with container:
        #andiamo a prendere i dati dal nostro database SQLite
        #e a creare una lista con le informazioni delle analisi effettuate 
        #in modo da poterle visualizzare in un formato tabellare
            view_analysis = filter_analyses()

        #qua definiamo una funzione per visualizzare i dettagli dell'analisi ed usiamo il decoratore @st.dialog per creare un dialogo
        #che ci permetta di visualizzarli
        @st.dialog(width = "large", title= current_lang.get('analysis_details', 'Analysis Details'))
        def view_analysis_details(analysis_id, analysis_name, analysis_date, current_lang):
            #qua andiamo a salvare i dati dell'analisi selezionata nella sessione
            #in modo da poterli utilizzare in seguito per il download del file
            st.session_state['selected_analysis_name'] = analysis_name
            st.session_state['selected_analysis_id'] = analysis_id
            st.session_state['uploaded_file_name'] = analysis_name   

            #andiamo a recuperare i dati dell'analisi dal database
            analysis_data = get_data_analysis(analysis_id)

            if not analysis_data:
                st.error(current_lang.get("data_not_found", "Analysis data not found."))
                return
            col1, col2 = st.columns(2)
            with col1:
                st.subheader(analysis_name)
            with col2:
                st.write(f"{current_lang.get('analysis_date', 'Date')}: {analysis_date}")

                #andiamo ad unire i dati dell'analisi con i dati del file blob
                #e a creare un file temporaneo per visualizzare il documento
            temp_file_path = os.path.join(temp_files_dir, f"temp_view_{analysis_id}.pdf")
            try:
                blob_data = analysis_data.get("file_blob")
                if blob_data:
                    with open(temp_file_path, "wb") as temp_file:
                        temp_file.write(blob_data)
                else:
                    st.error(current_lang.get("data_not_found", "File data is missing."))
                    st.button(current_lang.get("close_analysis", "Close"), key=f"close_dialog_{analysis_id}")
                    return
            except Exception as e:
                st.error(current_lang.get("rectangle_error", "Error").format(error=e))
                return

            # Configuriamo lo stato della sessione per edit_data
            history_session_key = f"history_view_{analysis_id}"
            if history_session_key not in st.session_state:
                st.session_state[history_session_key] = {}

            # Salviamo il percorso del file nella sessione per edit_data
            st.session_state['temporary_file_path'] = temp_file_path

            #richiamiamo la funzione edit_data dal frontend
            # e gli passiamo i dati dell'analisi
            edit_data(analysis_data, current_lang=current_lang)

            # Pulizia del file temporaneo usando la funzione delete_temp_file dal frontend
            try:
                delete_temp_file(temp_file_path)
            except Exception as e:
                logging.error(f"Error deleting temporary file: {e}")

        # se la view_analysis è vuota, mostriamo un messaggio di avviso altrimenti mostriamo la cronologia delle analisi 
        # e un bottone per visualizzare i dettagli
        if view_analysis:
            history_data = []
            for analysis in view_analysis:
                analysis_id = analysis[0]
                analysis_name = analysis[1]
                analysis_date = analysis[2]

            #poniamo un blocco try-except per gestire eventuali errori durante la visualizzazione della data
                #andiamo a formattare la data in un formato leggibile
                try:
                    date_obj = datetime.datetime.strptime(analysis_date, "%Y-%m-%d %H:%M:%S")
                    formatted_date = date_obj.strftime("%d %b %Y, %H:%M")
                except:
                    formatted_date = analysis_date

                history_data.append({
                    "ID": analysis_id,
                    "Name": analysis_name,
                    "Date": formatted_date,
                    "Action": analysis_id
                })
            
            df = pd.DataFrame(history_data)

        #per ciascun'analisi andiamo a creare una lista con le informazioni delle analisi effettuate
            for _, row in df.iterrows():
                col1, col2, col3 = st.columns([4, 1.8, 1])

                with col1:
                    st.write(f"**{row['Name']}**")

                with col2:
                    st.write(f"📅 {row['Date']}")

                with col3:
                    if st.button(current_lang.get("view_analysis", "View"), key=f"view_{row['ID']}"):
                        view_analysis_details(row['ID'], row['Name'], row['Date'], current_lang)

                st.divider()
        else:
            st.info(current_lang.get("history_info", "No analysis history available."))