import streamlit as st
import json
import logging
import pandas as pd
import os
import io
from io import BytesIO
from PIL import Image, ImageDraw
import streamlit.components.v1 as components
from backend import analyze_invoice, download_button, create_annotated_image
from database import create_database, add_analysis_history, get_crono, get_data_analysis, delete_oldest_analysis
import pymupdf
from dotenv import load_dotenv

load_dotenv()

#settiamo la lingua di default in italiano, se non è già presente nella sessione
if 'language' not in st.session_state:
    st.session_state['language'] = 'IT' 

#andiamo a caricare i nostri file temporanei in una cartella specifica
temp_files_dir = "temp_files"
os.makedirs(temp_files_dir, exist_ok=True)

#mettiamo la cartella temporanea in una variabile di sessione, in modo tale da non doverla creare ogni volta
if 'temp_files_dir' not in st.session_state:
    st.session_state.temp_files_dir = temp_files_dir

# configuriamo la nostra pagina per visualizzare tutto centralmente, ed impostando il titolo
st.set_page_config(
    page_title="Data Extractor",
    layout="wide",
    initial_sidebar_state="auto",
)

# andiamo a definire le traduzioni in un dizionario, in modo tale da poterle usare in base alla lingua selezionata
translations = {
    "IT": {
        "login_prompt": "Effettua il login per continuare",
        "login_button": "Log in",
        "analysis_history": "Cronologia Analisi",
        "analysis_info": "Informazioni sui prodotti",
        "first_title": ":blue-background[Benvenuto nel nostro potente :blue[Azure AI] Data Extractor!]",
        "second_title": "Analizza i tuoi documenti e lascia che il nostro AI faccia il resto 🚀",
        "third_title": "In seguito potrai modificare i dati estratti, visualizzare il file caricato con i campi evidenziati e scaricare il file in formato JSON. ⬇️",
        "info_textinput": "Informazioni sul Venditore",
        "no_analysis_history": "Non ci sono analisi in cronologia.",
        "clear_warning": "Sei sicuro di voler cancellare tutta la cronologia? Questa azione non può essere annullata.",
        "clear_history": "🗑️ Pulisci Cronologia",
        "confirm_clear_history": "Sì, Pulisci Cronologia",
        "cancel_clear_history": "Annulla",
        "clear_success": "Cronologia cancellata con successo.",
        "view_analysis": "Apri Analisi",
        "analysis_details": "Dettagli Analisi",
        "close_analysis": "Chiudi",
        "history_info" : "Non è disponibile alcuna analisi in cronologia.",
        "logout_button": "Log out",
        "greeting": "Ciao, **{name}**, {email}",
        "upload_label": "Carica una Fattura o una Ricevuta",
        "success_upload": "File {file_name} caricato con successo",
        "extract_image": "Immagine con bounding box",
        "error_upload": "Errore durante l'analisi del documento: {error}",
        "json_success": "Dati aggiornati e file JSON scaricato con successo!",
        "json_error": "Errore durante l'aggiornamento dei dati e il download: {error}",
        "text_input": ["Nome Venditore","Indirizzo Venditore","Numero di telefono Venditore","Data","Orario","PIVA","Totale"],
        "dataframe_columns": ["Descrizione", "Codice Prodotto", "Quantità", "PrezzoUnità", "Totale"],
        "update_download_button": "Aggiorna e Scarica Dati",
        "analyze_selected": "Analisi selezionata:",
        "no_file_warning": "Non è stato caricato alcun file, seguire le istruzioni corrette",
        "unsupported_file_error": "Tipo di file non supportato caricato: {file_name}",
        "invalid_file_error": "File {file_type} non valido caricato: {file_name}",
        "data_extraction_error": "Impossibile estrarre i dati dal documento.",
        "temp_path" : "Il percorso temporaneo del file non è definito.",
        "analyzing_document": "Analizzando il documento...",
        "ocr_error": "Errore durante l'OCR e la generazione del PDF: {error}",
        "rectangle_error": "Errore durante il disegno dei rettangoli: {error}",
        "data_not_found": "I dati del file per questa analisi sono mancanti."
    },
    "EN": {
        "login_prompt": "Please log in to continue",
        "login_button": "Log in",
        "analysis_history": "Analysis History",
        "analysis_info": "Product Information",
        "first_title": ":blue-background[Welcome to our powerful :blue[Azure AI] Data Extractor!]",
        "second_title": "Analyze your documents and let our AI do the rest 🚀",
        "third_title": "Then you can edit the extracted data, view the uploaded file with highlighted fields, and download the file in JSON format. ⬇️",
        "info_textinput": "Vendor Information",
        "no_analysis_history": "There are no analyses in history.",
        "clear_warning": "Are you sure you want to clear all history? This action cannot be undone.",
        "clear_history": "🗑️ Clear All History",
        "confirm_clear_history": "Yes, Clear History",
        "cancel_clear_history": "Cancel",
        "clear_success": "History cleared successfully.",
        "view_analysis": "Open Analysis",
        "analysis_details": "Analysis Details",
        "close_analysis": "Close",
        "logout_button": "Log out",
        "greeting": "Hello, **{name}**, {email}",
        "upload_label": "Upload an Invoice or a Receipt",
        "success_upload": "File {file_name} uploaded successfully",
        "extract_image": "Image with bounding box",
        "error_upload": "Error during document analysis: {error}",
        "json_success": "Data updated and JSON file downloaded successfully!",
        "json_error": "Error during the data update and download: {error}",
        "text_input": ["Vendor Name", "Vendor Address", "Vendor Phone Number", "Date", "Time", "VAT Number", "Total"],
        "dataframe_columns": ["Description", "Product Code", "Quantity", "Unit Price", "Total"],
        "update_download_button": "Update and Download Data",
        "analyze_selected": "Analyze selected:",
        "no_file_warning": "There's no file uploaded, please follow the right instructions",
        "unsupported_file_error": "Unsupported file type uploaded: {file_name}",
        "invalid_file_error": "Invalid {file_type} file uploaded: {file_name}",
        "data_extraction_error": "Failed to extract data from the document.",
        "temp_path" : "The temporary file path is not defined.",
        "analyzing_document": "Analyzing the document...",
        "ocr_error": "Error during OCR and PDF generation: {error}",
        "rectangle_error": "Error during rectangle drawing: {error}",
        "data_not_found": "File data for this analysis is missing."
    },
    "ES": {
        "login_prompt": "Inicia sesión para continuar",
        "login_button": "Iniciar sesión",
        "analysis_history": "Historial de análisis",
        "analysis_info": "Información sobre los productos",
        "first_title": ":blue-background[Bienvenido a nuestro potente :blue[Azure AI] Data Extractor!]",
        "second_title": "Analiza tus documentos y deja que nuestra IA haga el resto 🚀",
        "third_title": "Luego podrás editar los datos extraídos, ver el archivo cargado con los campos resaltados y descargar el archivo en formato JSON.⬇️",
        "info_textinput": "Informaciòn del Vendedor",
        "no_analysis_history": "No hay análisis en el historial.",
        "clear_warning": "¿Estás seguro de que deseas limpiar todo el historial? Esta acción no se puede deshacer.",
        "clear_history": "🗑️ Limpiar todo el historial",
        "confirm_clear_history": "Sí, limpiar historial",
        "cancel_clear_history": "Cancelar",
        "clear_success": "Historial limpiado con éxito.",
        "view_analysis": "Abrir análisis",
        "analysis_details": "Detalles del análisis",
        "close_analysis": "Cerrar",
        "history_info" : "No hay análisis disponibles en el historial.",
        "logout_button": "Cerrar sesión",
        "greeting": "Hola, **{name}**, {email}",
        "upload_label": "Cargar una factura o un recibo",
        "success_upload": "Archivo {file_name} cargado con éxito",
        "extract_image": "Imagen con bounding box",
        "error_upload": "Error al analizar el documento: {error}",
        "json_success": "Datos actualizados y archivo JSON descargado con éxito!",
        "json_error": "Error al actualizar los datos y descargar: {error}",
        "text_input": ["Nombre del vendedor", "Dirección del vendedor", "Número de teléfono del vendedor", "Fecha", "Hora", "Número de IVA", "Total"],
        "dataframe_columns": ["Descripción", "Código de producto", "Cantidad", "Precio unitario", "Total"],
        "update_download_button": "Actualizar y descargar datos",
        "analyze_selected": "Análisis seleccionado:",
        "no_file_warning": "No se ha cargado ningún archivo, siga las instrucciones correctas",
        "unsupported_file_error": "Tipo de archivo no compatible cargado: {file_name}",
        "invalid_file_error": "Archivo {file_type} no válido cargado: {file_name}",
        "data_extraction_error": "No se pudieron extraer datos del documento.",
        "temp_path" : "La ruta del archivo temporal no está definida.",
        "analyzing_document": "Analizando el documento...",
        "ocr_error": "Error durante el OCR y la generación del PDF: {error}",
        "rectangle_error": "Error al dibujar los rectángulos: {error}",
        "data_not_found": "Los datos del archivo para este análisis faltan."

    }
}

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
            lang = st.selectbox(
                "A", 
                ["IT", "EN", "ES"], 
                label_visibility="hidden",
                key="dashboard_lang_selector",
                index=["IT", "EN", "ES"].index(st.session_state['language']),  
                on_change=lambda: st.session_state.update(language=st.session_state.dashboard_lang_selector) 
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
    """Display consistent navigation buttons in the sidebar."""
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
                    

#la funzione per gestire il file che viene caricato, se non è vuota allora il file
#viene letto, andando a verificare però che il file sia un file pdf, ed in caso creando
#un file temporaneo per esso, in caso contrario restituisce errore, con qualche log pure
    def handle_file_upload(uploaded_file):
        if uploaded_file is not None:
            file_content = uploaded_file.read()
            file_type = uploaded_file.type
            file_extension = uploaded_file.name.split(".")[-1].lower()
            is_image = file_extension in ("jpg", "jpeg", "png")

#definiamo la funzione per i PDF, di solito i primi bytes contengono %PDF quindi ci basta questo
#per assicurarci lo sia, invece per le img, potendo avere schemi differenti, non sempre è così, quindi
#usiamo la lib Pillow e il modulo io per aprire e verificare il contenuto
            temporary_file_path = os.path.join(temp_files_dir, "temp.pdf")

            def file_PDF(file_content):
                return file_content.startswith(b'%PDF')

            def file_IMG(file_content):
                try:

                    img = Image.open(io.BytesIO(file_content))
                    img.verify() 
                    return True
                except Exception as e:
                    logging.warning(f"Invalid image file: {e}")
                    return False
            #qua poniamo una condizione per verificare se il file è un immagine ed esiste, allora andiamo a 
            #creare un file temporaneo in pdf, in caso contrario andiamo a verificare se è un pdf
            if is_image and file_IMG(file_content):
                try:
                    #andiamo a aprire il nostro file content e lo mettiamo in una variabile
                    img = Image.open(io.BytesIO(file_content))
                    
                    doc = pymupdf.open()
                    page = doc.new_page(width=img.width, height=img.height)
                    
                    #qua andiamo a convertire l'immagine in bytes 
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="PNG")
                    img_bytes.seek(0)
                    
                    #qua aggiungiamo l'immagine alla pagina PDF ed infine lo salviamo in un file temporaneo
                    page.insert_image(page.rect, stream=img_bytes.getvalue())
                    doc.save(temporary_file_path)
                    doc.close()
                    
                    #andiamo a leggere il file temporaneo in formato binario
                    with open(temporary_file_path, "rb") as pdf_file:
                        pdf_content = pdf_file.read()
                    
                    logging.info(f"Image file {uploaded_file.name} converted to PDF and saved to temporary path.")
                    return temporary_file_path, pdf_content
                    
                except Exception as e:
                    logging.error(f"Error converting image to PDF: {e}")
                    st.error(f"Error processing image: {e}")
                    return None, None
            
            #in caso non sia un immagine andiamo a verificare se è un pdf, in caso contrario restituiamo errore
            elif file_type == "application/pdf" or file_extension == "pdf":
                if file_PDF(file_content):
                    with open(temporary_file_path, "wb") as temporary_file:
                        temporary_file.write(file_content)
                    logging.info(f"PDF file {uploaded_file.name} saved to temporary path.")
                    return temporary_file_path, file_content
                else:
                    logging.warning(f"Invalid PDF file uploaded: {uploaded_file.name}")
                    st.error(current_lang["invalid_file_error"].format(file_type="PDF", file_name=uploaded_file.name))
                    return None, None
            else:
                logging.warning(f"Unsupported file type uploaded: {file_type} - {uploaded_file.name}")
                st.error(current_lang["unsupported_file_error"].format(file_name=uploaded_file.name))
                return None, None
        else:
            logging.warning("There's no file uploaded, please follow the right instructions")
            st.warning(current_lang["no_file_warning"])
            return None, None

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
                    has_ocr_data = 'ocr_pdf_bytes' in st.session_state and st.session_state['ocr_pdf_bytes']
                    has_original_image = 'original_image' in st.session_state
                    
                    st.header(current_lang["extract_image"])
                        #se sono presenti andiamo a creare l'immagine con i bounding box richiamando la funzione
                        #create_annotated_image dal backend, altrimenti andiamo a visualizzare l'immagine originale
                    if has_file_blob and has_polygons:
                        
                        try:
                            annotated_image = create_annotated_image(data["file_blob"], data["polygons"])
                            if annotated_image:
                                st.image(annotated_image, width=500)
                                logging.info("Successfully displayed annotated image with bounding boxes")
                                display_successful = True
                            else:
                                raise ValueError("Annotated image creation returned None")
                        except Exception as anno_e:
                            logging.warning(f"Failed to create annotated image: {anno_e}")
                            display_successful = False
                            
                                    #andiamo a aprire il file pdf, lo convertiamo in immagine, salviamo
                                    #l'immagine in un buffer e la mostriamo, altrimenti mostriamo l'immagine originale
                            if has_ocr_data:
                                try:
                                    
                                    ocr_doc = pymupdf.open("pdf", st.session_state['ocr_pdf_bytes'])
                                    page = ocr_doc[0]
                                    pix = page.get_pixmap()
                                    
                                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                                    draw = ImageDraw.Draw(img)
                                    
                                    #prendiamo le dimensioni dell'immagine 
                                    img_width, img_height = img.size
                                    
                                    #per ogni poligono presente andiamo a calcolare le coordinate e poi a disegnare il rettangolo
                                    for polygon in data["polygons"]:
                                        if "polygon" in polygon and len(polygon["polygon"]) >= 4:
                                            points = polygon["polygon"]
                                            x_coords = [p["x"] for p in points]
                                            y_coords = [p["y"] for p in points]
                                            
                                            x0, y0 = min(x_coords), min(y_coords)
                                            x1, y1 = max(x_coords), max(y_coords)
                                            #andiamo a scalare le coordinate in base alla dimensione dell'immagine, normalizzando prima
                                            #le coordinate in un range 0-1 e scalando in base alla dimensione dell'immagine
                                            doc_width = st.session_state.get('doc_dimensions', {}).get('width', page.rect.width)
                                            doc_height = st.session_state.get('doc_dimensions', {}).get('height', page.rect.height)
                                            
                                            x0_norm = x0 / doc_width
                                            y0_norm = y0 / doc_height
                                            x1_norm = x1 / doc_width
                                            y1_norm = y1 / doc_height
                                            
                                            x0_px = x0_norm * img_width
                                            y0_px = y0_norm * img_height
                                            x1_px = x1_norm * img_width
                                            y1_px = y1_norm * img_height
                                            
                                            #qui infine andiamo a disegnare il rettangolo usando le 
                                            #coordinate calcolate prima dal poligono
                                            draw.rectangle([(x0_px, y0_px), (x1_px, y1_px)], outline="red", width=3)
                                            
                                    #come detto prima, andiamo poi a convertire l'immagine in bytes e infine chiudiamo il file
                                    img_bytes = io.BytesIO()
                                    img.save(img_bytes, format='PNG')
                                    img_bytes.seek(0)
                                    
                                    st.image(img_bytes, width=500)
                                    logging.info("Successfully displayed OCR image with bounding boxes")
                                    display_successful = True
                                    
                                    ocr_doc.close()
                                    
                                except Exception as ocr_display_e:
                                    logging.warning(f"Failed to display OCR image with bounding boxes: {ocr_display_e}")
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
                                    st.image(img_bytes, width=500)
                                    doc.close()
                                except Exception as pdf_e:
                                    logging.error(f"Failed to render PDF for display: {pdf_e}")
                                    st.error(f"Could not render PDF: {pdf_e}")
                            else:
                                st.image(data["file_blob"], width=500)
                        elif has_original_image:
                            #se i poligoni non sono presenti andiamo a mostrare l'immagine originale
                            st.image(st.session_state['original_image'], width=500)
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
                                        st.image(file_content, width=500)
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
                    file_name = f"{st.session_state.get('selected_analysis_name')}.json"
                else:
                    file_name = f"{st.session_state.get('uploaded_file_name')}.json"
                download_html = download_button(buff.getvalue(), file_name) 
                components.html(
                    download_html,
                    height=0,
                )
                logging.info(f"JSON file {st.session_state['uploaded_file_name']}.json downloaded successfully.")
                st.rerun()

            except Exception as e:
                logging.error(f"Error during the data update and download: {e}")
                st.error(current_lang["json_error"].format(error=e))
            st.success(current_lang["json_success"])
        return data_it

#andiamo a definire una funzione per eliminare il file temporaneo, in modo tale da non sovraccaricare il database
#e mantenere solo le più recenti, in caso di errore restituisce un log di errore
    def delete_temp_file(file_path):
        #se il file non è definito, non facciamo nulla
        #altrimenti andiamo a dare il permesso di eliminare il file
        if not file_path:
            return
            
        try:
            #andiamo a definire il numero di tentativi per eliminare il file e per ogni tentativo
            #verifichiamo se il file esiste, in caso contrario non facciamo nulla
            attempts = 3
            for i in range(attempts):
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logging.info(f"Temporary file {file_path} deleted successfully.")
                        break
                    except PermissionError as pe:
                        if i < attempts - 1:
                            logging.warning(f"File {file_path} is locked. Waiting before retry #{i+1}.")
                        else:
                            logging.warning(f"Could not delete {file_path} after {attempts} attempts: {pe}")
                else:
                    #se il file non esiste, non facciamo nulla
                    break
        except Exception as e:
            logging.error(f"Error deleting temporary file {file_path}: {e}")

if st.session_state.get('current_page') != 'history':
    st.markdown(f"<h1 style='text-align: center;'>{current_lang['first_title'].replace(':blue[Azure AI]', '<span style=\"color:blue;\">Azure AI</span>').replace(':blue-background[', '<span style=\"background-color:#b3d7fe;\">').replace(']', '</span>')}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center; font-weight: bold;'>{current_lang['second_title']}</h3>", unsafe_allow_html=True)
    st.markdown(f"<h5 style='text-align: center;'>{current_lang['third_title']}</h3>", unsafe_allow_html=True)
    st.markdown("---")

    #usiamo la funzione di streamlit per caricare un file pdf e consentire solo quel formato
    st.markdown(f"### :receipt: {current_lang['upload_label']}<div style='margin-bottom: -70px;'></div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        label=current_lang["upload_label"], 
        type=["pdf", "jpg","png", "jpeg"],
        key="file_uploader",
        label_visibility="hidden",
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

#se il file è stato caricato con successo , gestiamo l'upload con la nostra funzione
#e creiamo un file temporaneo, che verrà aperto in formato binario e verrà letto restituendo
#estracted_data come variabile, in caso contrario restituisce un errore durante l'aalisi del documento
    if uploaded_file is not None:
        #inseriamo la variabile di sessione per l'uploaded_file in modo tale da
        #riavviare l'analisi in caso di cambio file caricato, resettando i dati estratti
        if uploaded_file.name != st.session_state.get('uploaded_file_name'):
        
            st.session_state['extracted_data'] = None  
            st.session_state['uploaded_file_name'] = uploaded_file.name
            if st.session_state['temporary_file_path']:
                delete_temp_file(st.session_state['temporary_file_path'])
                st.session_state['temporary_file_path'] = None

        st.success(current_lang["success_upload"].format(file_name=uploaded_file.name))
        logging.info(f"File {uploaded_file.name} uploaded successfully.")

        temporary_file_path, file_content = handle_file_upload(uploaded_file)

        if temporary_file_path:
            if st.session_state['extracted_data'] is None or st.session_state['temporary_file_path'] != temporary_file_path:
                st.session_state['temporary_file_path'] = temporary_file_path

            if st.session_state['extracted_data'] is None:
                with st.spinner(current_lang["analyzing_document"]):
                    logging.info("Analyzing the document...")
                    try:
                        with open(temporary_file_path, "rb") as f: 
                            file_content = f.read()
                            
                            #andiamo, con un try-except, ad aprire il file temporaneo in formato binario,
                            #selezioniamo la prima pagina e generiamo un pixmap senza canale alpha
                            #per evitare problemi di OCR, in caso di errore andiamo a restituire un errore
                            try:
                                doc = pymupdf.open(temporary_file_path)
                                page = doc[0]
                                pix = page.get_pixmap(alpha=False)
                                
                                #andiamo a creare un’immagine a partire dai dati del pixmap, salvata in un buffer 
                                # di memoria e poi la memorizziamo nella session state
                                img_bytes_original = io.BytesIO()
                                img_original = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                img_original.save(img_bytes_original, format='PNG')
                                img_bytes_original.seek(0)
                                st.session_state['original_image'] = img_bytes_original.getvalue()
                                
                                #andiamo a memorizzare le dimensioni del documento nella session state
                                #per poterle usare in seguito per il disegno dei bounding box
                                st.session_state['doc_dimensions'] = {
                                    'width': page.rect.width,
                                    'height': page.rect.height
                                }
                                
                                #andiamo a richiamare il metodo pdfocr_tobytes per generare un PDF che incorpora i risultati OCR,
                                #settando i vari parametri come compressione, lingua e percorso tessdata
                                ocr_pdf_bytes = pix.pdfocr_tobytes(
                                    compress=True,
                                    language='eng+ita',
                                    tessdata= os.getenv("TESSDATA_PREFIX"),
                                )
                                
                                #andiamo a memorizzare il PDF OCR nella session state
                                #in modo tale da poterlo usare in seguito per il disegno dei bounding box ed infine chiudiamo il file
                                st.session_state['ocr_pdf_bytes'] = ocr_pdf_bytes
                                logging.info("OCR processing completed successfully")
                                
                                doc.close()
                                
                            except Exception as ocr_e:
                                logging.warning(f"OCR processing failed: {ocr_e}")
                                st.session_state['ocr_pdf_bytes'] = None
            
                            st.session_state['extracted_data'] = analyze_invoice(file_content)
                            st.session_state['extracted_data']["file_blob"] = file_content
                        
                    #andiamo a controllare se la cronologia è piena, se vi sono più di 10 analisi allora
                    #andiamo a cancellare la più vecchia
                        view_analysis = get_crono()
                        if len(view_analysis) >= 10:
                            oldest_analysis = view_analysis[-1] 
                            oldest_id = oldest_analysis[0]
                            oldest_temp_file_path = os.path.join(temp_files_dir, f"temp_{oldest_id}.pdf")
                            delete_temp_file(oldest_temp_file_path)
                            delete_oldest_analysis()
                            logging.info("Oldest analysis deleted to maintain history size limit.")

                    # rimuoviamo temporaneamente il blob dai dati estratti ed usiamo add_analysis_history per salvare 
                    # sia i dati estratti che il file come blob, per poi ripristinare il blob
                        file_blob = st.session_state['extracted_data'].pop("file_blob", None)
                        add_analysis_history(st.session_state['uploaded_file_name'], st.session_state['extracted_data'], file_blob)
                        if file_blob: 
                            st.session_state['extracted_data']["file_blob"] = file_blob
                            
                        logging.info("Document analysis completed successfully.")
                        st.session_state['analysis_source'] = 'new'
                        st.rerun()
                    except Exception as e:
                        logging.error(f"Error during document analysis: {e}")
                        st.error(current_lang["error_upload"].format(error=e))
                        st.session_state['extracted_data'] = None
                        logging.error("Document analysis failed.")

            #se i dati estratti sono presenti usiamo la funzione per poter permettere la 
            #modifica di essi, in caso contrario restituisce un errore di estrazione dati
            #inoltre andiamo a salvare i dati estratti nel database, in modo tale da poterli
            #recuperare in un secondo momento, e mostrare la cronologia delle analisi
            if st.session_state['extracted_data']:
                if st.session_state['analysis_source'] == 'new':
                    st.header(current_lang["analysis_info"])
                    edit_data(st.session_state['extracted_data'], current_lang=current_lang, key_prefix="new_upload")

                else:
                    logging.info("Skipping duplicate display for new analysis.")
            else:
                st.error(current_lang["data_extraction_error"])
                logging.error("Failed to extract data from the document.")
        else:
            logging.warning("File upload failed.")
            st.warning(current_lang["no_file_warning"])

#se la sessione è già stata avviata e i dati estratti sono presenti,
#andiamo a mostrare la cronologia delle analisi effettuate, in modo tale da poterle visualizzare
#ed usando la query_params per mostrare i dati estratti in base all'get_analysis selezionata
    if "all_history" in st.session_state and st.session_state['extracted_data']:
        if st.session_state['analysis_source'] != 'new':
            st.header(current_lang["analysis_info"].format(st.session_state['uploaded_file_name']))
            edit_data(st.session_state['extracted_data'], key_prefix="history_view", show_image_with_bbox=True)

    query_params = st.query_params

    
    if "get_analysis" in query_params:
        id_get_analysis = int(query_params["get_analysis"][0])
        dati_get_analysis = get_data_analysis(id_get_analysis)
        if dati_get_analysis:
            st.session_state['extracted_data'] = dati_get_analysis
            st.session_state['uploaded_file_name'] = next(
                (op[1] for op in view_analysis if op[0] == id_get_analysis), None
            )
