import streamlit as st
import json
import logging
import pandas as pd
import os
import io
from io import BytesIO
from PIL import Image
import streamlit.components.v1 as components
from backend.analyze_func import *
from backend.database import *
from backend.download import download_button
from backend.lang import translations, set_language
from backend.tempfile_del import delete_temp_file
from backend.files_ocr import *
import pymupdf
from dotenv import load_dotenv

load_dotenv()
set_language()
#mettiamo la cartella temporanea in una variabile di sessione, in modo tale da non doverla creare ogni volta
if 'temp_files_dir' not in st.session_state:
    st.session_state.temp_files_dir = temp_files_direct()

# configuriamo la nostra pagina per visualizzare tutto centralmente, ed impostando il titolo
st.set_page_config(
    page_title="Data Extractor ",
    layout="wide",
    initial_sidebar_state="auto",
)

#connettiamoci al nostro db andando a prendere la conn ed il cursore presente nel nostro file database
create_database()

with st.sidebar:
    if st.session_state.get("current_page") != "history":
        # Creiamo due colonne nel sidebar per allineare Logo+Titolo e Selectbox
        col1, col2 = st.columns(2, vertical_alignment="top")
        with col1:
            st.logo("https://www.oaks.cloud/_next/static/media/oaks.1ea4e367.svg",    #inseriamo il logo dell'azienda nella nostra app
                size="large",
                link="https://www.oaks.cloud/")
            ""
            st.title(":globe_with_meridians:**Dashboard**")
        with col2:
            #andiamo a selezionare la lingua, in modo tale da poterla cambiare in base alla selezione dell'utente
            if 'language' not in st.session_state:
                st.session_state.language = 'IT'
            
            lang = st.selectbox(
                "A", 
                ["IT", "EN", "ES"], 
                label_visibility="hidden",
                index=["IT", "EN", "ES"].index(st.session_state['language']),
                key="dashboard_lang_selector"
            )
            #andiamo a salvare la lingua selezionata nella sessione, in modo tale da non doverla cambiare ogni volta
            if lang != st.session_state['language']:
                st.session_state['language'] = lang

            # selezioniamo il dizionario della lingua corrente in base alla selezione dell'utente
            current_lang = translations[st.session_state['language']]
            st.session_state.translations = translations

# andiamo a configurare i nostri log, creando un file a parte per visualizzarli
logging.basicConfig(
    filename="app.log",  # Commentare questa riga per inviare i log a stdout (per Docker)
    encoding="utf-8",
    filemode="a",       # Questa riga aggiunge i vecchi log ai nuovi, append mode
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
    level=logging.INFO
)

def show_navigation(page_prefix=""):
    if st.button(":house:**Homepage**", use_container_width=True, key=f"{page_prefix}_dashboard_btn"):
        st.session_state['current_page'] = 'dashboard'
        st.switch_page("frontend.py")
    if st.button("📜 History", use_container_width=True, key=f"{page_prefix}_history_btn"):
        st.session_state['current_page'] = 'history'
        st.switch_page("pages/1_🧾_History.py")

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
        if st.session_state.get("current_page") != "history":
            if st.user.is_logged_in:
                st.markdown(current_lang["greeting"].format(name=st.user.name, email=st.user.email))
                logging.info(f"User {st.user.name} ({st.user.email}) successfully logged in.")

                if st.button(current_lang["logout_button"]):
                    st.logout()
                st.markdown("---")
                st.markdown("")
            show_navigation(page_prefix="dashboard")
                    

#definiamo una funziona avente come parametro i nostri dati
    def edit_data(data, current_lang, key_prefix="", show_image_with_bbox=True):
        data_it = {}

        # qua creiamo una lista di dizionari per rappresentare gli elementi estratti e ciascun dizionario contiene le 
        # colonne del dataframe come chiavi e i valori corrispondenti dagli elementi estratti
        if "Items" in data:
            if data["Items"]:
                items = []
                for item in data["Items"]:
                    item_dict = {}
                    for i, key in enumerate(item.keys()):
                        column_name = current_lang["dataframe_columns"][i]
                        item_dict[column_name] = item.get(key, None)
                    items.append(item_dict)
                df = pd.DataFrame(items, columns=current_lang["dataframe_columns"])
            else:
                df = pd.DataFrame(columns=current_lang["dataframe_columns"])

        edited_df = st.data_editor(df, num_rows="dynamic", key=f"{key_prefix}_items_df")
        lista_prodotti = edited_df.to_dict("records")

        #creiamo un form per poter modificare i dati in italiano, con i parametri che andremo ad aggiornare
        with st.form(key=f"{key_prefix}_edit_form"):
            st.header(current_lang["info_textinput"])
            data_it["Nome Venditore"] = st.text_input(current_lang["text_input"][0], value=data.get("VendorName", "N/A"), key=f"{key_prefix}_vendor_name")
            data_it["Indirizzo Venditore"] = st.text_input(current_lang["text_input"][1], value=data.get("VendorAddress", "N/A"), key=f"{key_prefix}_vendor_address")
            data_it["Numero di telefono Venditore"] = st.text_input(current_lang["text_input"][2], value=data.get("MerchantPhoneNumber", "N/A"), key=f"{key_prefix}_vendor_phone")
            data_it["Data"] = st.text_input(current_lang["text_input"][3], value=data.get("InvoiceDate", "N/A"), key=f"{key_prefix}_invoice_date")
            data_it["Orario"] = st.text_input(current_lang["text_input"][4], value=data.get("TransactionTime", "N/A"), key=f"{key_prefix}_transaction_time")
            data_it["PIVA"] = st.text_input(current_lang["text_input"][5], value=data.get("VendorTaxId", "N/A"), key=f"{key_prefix}_vendor_tax_id")
            data_it["Totale"] = st.text_input(current_lang["text_input"][6], value=data.get("InvoiceTotal", "N/A"), key=f"{key_prefix}_invoice_total")

        #se l'immagine con i bounding box è da mostrare, andiamo a controllare se il file blob è presente
        #se non è presente andiamo a cercare il file temporaneo, in caso contrario restituiamo errore
            if show_image_with_bbox:
                try:
                    #andiamo a verificare se il file blob, i poligoni, i dati ocr e l'immagine originale sono presenti,  
                    has_file_blob = "file_blob" in data and data["file_blob"]
                    has_polygons = "polygons" in data and data["polygons"]
                    has_original_image = 'original_image' in st.session_state
                    
                    st.header(current_lang["extract_image"])
                        #se sono presenti andiamo a creare l'immagine con i bounding box richiamando la funzione
                        #create_annotated_image dal backend, altrimenti andiamo a visualizzare l'immagine originale
                    if has_file_blob and has_polygons:
                        
                        try:
                            annotated_image = create_annotated_image(data["file_blob"], data["polygons"])
                            if annotated_image:
                                st.image(annotated_image)
                                logging.info("Successfully displayed annotated image with bounding boxes")
                                display_successful = True
                            else:
                                raise ValueError("Annotated image creation returned None")
                        except Exception as anno_e:
                            logging.warning(f"Failed to create annotated image: {anno_e}")
                            display_successful = False

                    else:
                        display_successful = False
                        
                    #in caso in cui non sia presente l'immagine con i bounding box, andiamo a verificare se il file blob è presente
                    #se è presente andiamo a verificare se è un pdf, in caso contrario andiamo a visualizzare l'immagine originale
                    if not display_successful:
                        if has_file_blob:
                            if data["file_blob"].startswith(b'%PDF'):
                                try:
                                    doc = pymupdf.open(stream=data["file_blob"], filetype="pdf")
                                    pix = doc[0].get_pixmap()
                                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                    img_bytes = io.BytesIO()
                                    img.save(img_bytes, format='PNG')
                                    img_bytes.seek(0)
                                    st.image(img_bytes)
                                    doc.close()
                                except Exception as pdf_e:
                                    logging.error(f"Failed to render PDF for display: {pdf_e}")
                                    st.error(f"Could not render PDF: {pdf_e}")
                            else:
                                st.image(data["file_blob"])
                        elif has_original_image:
                            #se i poligoni non sono presenti andiamo a mostrare l'immagine originale
                            st.image(st.session_state['original_image'])
                        else:
                            try:
                        # andiamo a controllare se la sessione è in cronologia
                        # e se il file temporaneo è presente, altrimenti restituiamo errore
                                if key_prefix == "history_view":
                                    history_session_key = f"history_{st.session_state['all_history']}"
                                    temporary_file_path = st.session_state[history_session_key].get('temporary_file_path')
                                else:
                                    temporary_file_path = st.session_state.get('temporary_file_path')
                                    
                                if temporary_file_path and os.path.exists(temporary_file_path):
                        #apriamo il file temporaneo in formato binario e lo leggiamo
                                    with open(temporary_file_path, "rb") as f:
                                        file_content = f.read()
                                        st.image(file_content)
                                else:
                                    st.warning("No image to display. The file may have been deleted.")
                            except Exception as temp_file_e:
                                logging.error(f"Failed to display temporary file: {temp_file_e}")
                                st.error("Could not display the document image.")
                
                except Exception as e:
                    logging.error(f"Error displaying image with bounding boxes: {e}")
                    st.error(current_lang["rectangle_error"].format(error=e))

            submit_button = st.form_submit_button(label=current_lang["update_download_button"])

        if submit_button:
            json_data_italiano = {
                "Nome Venditore": data_it["Nome Venditore"],
                "Indirizzo Venditore": data_it["Indirizzo Venditore"],
                "Numero di telefono Venditore": data_it["Numero di telefono Venditore"],
                "Data": data_it["Data"],
                "Orario": data_it["Orario"],
                "PIVA": data_it["PIVA"],
                "Totale": data_it["Totale"],
                "Lista Prodotti": lista_prodotti
            }

            #andiamo a tradurre le chiavi prese nella lingua selezionata, affinchè il file json sia nella lingua corretta
            translated_json_data = {}
            translated_json_data[current_lang["text_input"][0]] = json_data_italiano["Nome Venditore"]
            translated_json_data[current_lang["text_input"][1]] = json_data_italiano["Indirizzo Venditore"]
            translated_json_data[current_lang["text_input"][2]] = json_data_italiano["Numero di telefono Venditore"]
            translated_json_data[current_lang["text_input"][3]] = json_data_italiano["Data"]
            translated_json_data[current_lang["text_input"][4]] = json_data_italiano["Orario"]
            translated_json_data[current_lang["text_input"][5]] = json_data_italiano["PIVA"]
            translated_json_data[current_lang["text_input"][6]] = json_data_italiano["Totale"]
            product_list_key = {"IT": "Lista Prodotti", "EN": "Product List", "ES": "Lista de Productos"}[st.session_state['language']]
            translated_json_data[product_list_key] = lista_prodotti

        #usando un try-except per gestire eventuali errori, andiamo a creare un file json usando la libreria json e buffer
        #che andremo a scrivere e scaricare, in caso di successo restituisce un messaggio di successo, altrimenti un errore
        #relativo all'aggiornamento e download del file, restituisce i dati in italiano aggiornati 
            try:
                json_string = json.dumps(translated_json_data, indent=4, ensure_ascii=False)
                buff = BytesIO()
                buff.write(json_string.encode('utf-8'))
                buff.seek(0)

                
                if st.session_state.get("analysis_source") == "history":
                    file_name = f"{st.session_state.get('uploaded_file_name')}.json"
                else:
                    base_filename = key_prefix.replace("file_", "") if key_prefix.startswith("file_") else st.session_state.get('uploaded_file_name', 'extracted_data')
                    file_name = f"{base_filename}.json"
                download_html = download_button(buff.getvalue(), file_name) 
                components.html(
                    download_html,
                    height=0,
                )
                logging.info(f"JSON file {file_name} downloaded successfully.")

            except Exception as e:
                logging.error(f"Error during the data update and download: {e}")
                st.error(current_lang["json_error"].format(error=e))
            
            st.rerun()
        return data_it

    if st.session_state.get('current_page') != 'history':
        st.markdown(f"<h1 style='text-align: center;'>{current_lang['first_title'].replace(':blue[Azure AI]', '<span style=\"color:blue;\">Azure AI</span>').replace(':blue-background[', '<span style=\"background-color:#b3d7fe;\">').replace(']', '</span>')}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center; font-weight: bold;'>{current_lang['second_title']}</h3>", unsafe_allow_html=True)
        st.markdown(f"<h5 style='text-align: center;'>{current_lang['third_title']}</h3>", unsafe_allow_html=True)
        st.markdown("---")

        #usiamo la funzione di streamlit per caricare un file pdf e consentire solo quel formato
        if st.session_state['language'] == "IT":
            col_fileupload, col_filedelete = st.columns([14, 1], gap="small")
        elif st.session_state['language'] == "EN":
            col_fileupload, col_filedelete = st.columns([13, 1], gap="small")
        elif st.session_state['language'] == "ES":
            col_fileupload, col_filedelete = st.columns([13, 1], gap="small")

        with col_fileupload:
            st.markdown(
            f"### :receipt: {current_lang['upload_label']}",
            unsafe_allow_html=True
            )
        with col_filedelete:
            st.write("")
            #andiamo a creare un pulsante per eliminare i file caricati, se presenti
            if st.button(
                current_lang["delete_uploaded"],
                key="delete_uploaded_files"
            ):
                
                #andiamo ad inizializzare una nuova session state impostando il valore di file_uploader_reset a 1 in
                #caso non sia presente, altrimenti lo incrementiamo di 1 ogni volta che viene premuto il pulsante, 
                #in modo tale da forzare il refresh del file_uploader e resettarlo del tutto
                if 'file_uploader_reset' not in st.session_state:
                    st.session_state['file_uploader_reset'] = 1
                else:
                    st.session_state['file_uploader_reset'] += 1
                st.rerun()
        #impostiamo una chiave dinamica da mettere poi nel file_uploader, che va a prendere il valore di file_uploader_reset
        #se non è presente lo inizializziamo a 0, in modo tale da poterlo usare come chiave dinamica
        file_uploader_key = f"file_uploader_{st.session_state.get('file_uploader_reset', 0)}"
        uploaded_files = st.file_uploader(
            label=current_lang["upload_label"], 
            type=["pdf", "jpg","png", "jpeg"],
            key=file_uploader_key,
            label_visibility="hidden",
            accept_multiple_files=True
            )
        logging.info("Waiting for the file upload")

        #inizializziamo le variabili di sessione che andremo ad utilizzare
        if 'extracted_data' not in st.session_state:
            st.session_state['extracted_data'] = None
        if 'uploaded_file_name' not in st.session_state:
            st.session_state['uploaded_file_name'] = None
        if 'temporary_file_path' not in st.session_state:
            st.session_state['temporary_file_path'] = None
        if 'analysis_source' not in st.session_state:
            st.session_state['analysis_source'] = None
        if 'uploaded_files_data' not in st.session_state:
            st.session_state['uploaded_files_data'] = {}

    #se uploaded_files è presente allora per ciascun file in esso se il nome è già presente nella session
    #allora non analizza e passa alla prossima, gestiamo l'upload con la nostra funzione
    #e creiamo un file temporaneo, che verrà aperto in formato binario e verrà letto, in caso non sia stato
    #possibile analizzare il file, restituisce un errore

        col_home1, col_home2 = st.columns(2, gap="medium")
        if uploaded_files:
            for uploaded_file in uploaded_files:
                if uploaded_file.name in st.session_state['uploaded_files_data']:
                    st.info(current_lang["file_already_analyzed"].format(file_name=uploaded_file.name))
                    continue

                temporary_file_path, file_content = handle_file_upload(uploaded_file)
                st.success(f"{current_lang['success_upload'].format(file_name=uploaded_file.name)}")

                if temporary_file_path:
                    with st.spinner(current_lang["analyzing_document"]):
                        try:
                            with open(temporary_file_path, "rb") as f:
                                file_content = f.read()
                                
                                #andiamo, con un try-except, ad aprire il file temporaneo in formato binario,
                                #selezioniamo la prima pagina e generiamo un pixmap senza canale alpha
                                #per evitare problemi di OCR, in caso di errore andiamo a restituire un errore
                                try:
                                    try_ocr(temporary_file_path)
                                except Exception as ocr_e:
                                    logging.warning(f"OCR processing failed: {ocr_e}")
                                    st.session_state['ocr_pdf_bytes'] = None
                
                                analyzed_data = analyze_invoice(file_content)
                                analyzed_data["file_blob"] = file_content
                                analyzed_data["temporary_file_path"] = temporary_file_path
                                
                                #andiamo a inserire i nostri data analizzati ed estratti nella nostra session
                                st.session_state['uploaded_files_data'][uploaded_file.name] = analyzed_data
                                
                        #andiamo a controllare se la cronologia è piena, se vi sono più di 10 analisi allora
                        #andiamo a cancellare la più vecchia
                                view_analysis = get_crono()
                                if len(view_analysis) >= 10:
                                    oldest_analysis = view_analysis[-1] 
                                    oldest_id = oldest_analysis[0]
                                    oldest_temp_file_path = os.path.join(temp_files_direct(), f"temp_{oldest_id}.pdf")
                                    delete_temp_file(oldest_temp_file_path)
                                    delete_oldest_analysis()

                        # rimuoviamo temporaneamente il blob dai dati estratti ed usiamo add_analysis_history per salvare 
                        # sia i dati estratti che il file come blob, per poi ripristinare il blob
                                file_blob = analyzed_data.pop("file_blob", None)
                                add_analysis_history(uploaded_file.name, analyzed_data, file_blob)
                                if file_blob:
                                    analyzed_data["file_blob"] = file_blob
                                    
                                st.success(f"{current_lang["analysis_success"]} {uploaded_file.name}")
                                logging.info(f"Document analysis completed successfully for {uploaded_file.name}")
                                
                        except Exception as e:
                            logging.error(f"Error during document analysis: {e}")
                            st.error(current_lang["error_upload"].format(error=e))
                            st.session_state['extracted_data'] = None
                            break

                #per ogni file presente in sessione, usiamo un expander per la visualizzazione e
                #se i dati estratti sono presenti usiamo la funzione per poter permettere la 
                #modifica di essi, in caso contrario restituisce un errore di estrazione dati
                #inoltre andiamo a salvare i dati estratti nel database, in modo tale da poterli
                #recuperare in un secondo momento, e mostrare la cronologia delle analisi
            uploaded_files_list = list(st.session_state['uploaded_files_data'].items())
            if uploaded_files_list:
                col_left, col_right = st.columns(2, gap="medium")
                #mettiamo il primo file nella colonna di sinistra, expander aperto, tutti gli altri files
                #nella colonna di destra, expander chiuso
                filename_first, file_data_first = uploaded_files_list[0]
                with col_left:
                    with st.expander(f"**{current_lang["analysis_details"]}** -- {filename_first}", expanded=True):
                        st.header(f"**{current_lang["analysis_info"]}**")
                        edit_data(
                            file_data_first,
                            current_lang=current_lang,
                            key_prefix=f"file_{filename_first}",
                            show_image_with_bbox=True
                        )
                with col_right:
                    for filename, file_data in uploaded_files_list[1:]:
                        with st.expander(f"**{current_lang["analysis_details"]}** -- {filename}", expanded=False):
                            st.header(f"**{current_lang["analysis_info"]}**")
                            ""
                            edit_data(
                                file_data,
                                current_lang=current_lang,
                                key_prefix=f"file_{filename}",
                                show_image_with_bbox=True
                            )
            else:
                st.error(current_lang["data_extraction_error"])
                logging.error("Failed to extract data from the document.")
        else:
            logging.info("No files uploaded.")
            st.info(current_lang["no_file_warning"])