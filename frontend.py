import streamlit as st
import json
import logging
import pandas as pd
import os
import io
from io import BytesIO
from PIL import Image
import streamlit.components.v1 as components
from backend import analyze_invoice, download_button
import pymupdf
from PIL import ImageDraw
from dotenv import load_dotenv

load_dotenv()

# configuriamo la nostra pagina per visualizzare tutto centralmente, ed impostando il titolo
st.set_page_config(
    page_title="Data Extractor",
    layout="wide"
)

# andiamo a definire le traduzioni in un dizionario, in modo tale da poterle usare in base alla lingua selezionata
translations = {
    "IT": {
        "welcome_title": "Benvenuto nel nostro potente Estrattore AI di Dati!",
        "select_language": "Seleziona una lingua:",
        "home": "Home",
        "login_prompt": "Effettua il login per continuare",
        "login_button": "Log in",
        "logout_button": "Log out",
        "greeting": "Ciao, **{name}**, {email}",
        "extract_data_title": "Estrai :blue[Data] con :blue-background[Azure AI]",
        "upload_label": "Carica una Fattura o una Ricevuta",
        "success_upload": "File {file_name} caricato con successo",
        "error_upload": "Errore durante l'analisi del documento: {error}",
        "json_success": "Dati aggiornati e file JSON scaricato con successo!",
        "json_error": "Errore durante l'aggiornamento dei dati e il download: {error}",
        "product_list": "Lista di Prodotti",
        "update_download_button": "Aggiorna e Scarica Dati",
        "no_file_warning": "Non è stato caricato alcun file, seguire le istruzioni corrette",
        "unsupported_file_error": "Tipo di file non supportato caricato: {file_name}",
        "invalid_file_error": "File {file_type} non valido caricato: {file_name}",
        "data_extraction_error": "Impossibile estrarre i dati dal documento.",
        "analyzing_document": "Analizzando il documento...",
        "ocr_error": "Errore durante l'OCR e la generazione del PDF: {error}",
        "rectangle_error": "Errore durante il disegno dei rettangoli: {error}",
    },
    "EN": {
        "welcome_title": "Welcome to your powerful AI Data Extractor!",
        "select_language": "Select a language:",
        "home": "Home",
        "login_prompt": "Please log in to continue",
        "login_button": "Log in",
        "logout_button": "Log out",
        "greeting": "Hello, **{name}**, {email}",
        "extract_data_title": "Extract :blue[Data] with :blue-background[Azure AI]",
        "upload_label": "Upload an Invoice or a Receipt",
        "success_upload": "File {file_name} uploaded successfully",
        "error_upload": "Error during document analysis: {error}",
        "json_success": "Data updated and JSON file downloaded successfully!",
        "json_error": "Error during the data update and download: {error}",
        "product_list": "Product List",
        "update_download_button": "Update and Download Data",
        "no_file_warning": "There's no file uploaded, please follow the right instructions",
        "unsupported_file_error": "Unsupported file type uploaded: {file_name}",
        "invalid_file_error": "Invalid {file_type} file uploaded: {file_name}",
        "data_extraction_error": "Failed to extract data from the document.",
        "analyzing_document": "Analyzing the document...",
        "ocr_error": "Error during OCR and PDF generation: {error}",
        "rectangle_error": "Error during rectangle drawing: {error}",
    }
}

with st.sidebar:
    st.logo("https://www.oaks.cloud/_next/static/media/oaks.13e2f970.svg",    #inseriamo il logo dell'azienda nella nostra app
        size="large",
        link="https://www.oaks.cloud/")
    st.title(f":blue-background[**{translations['IT']['home']}**]")
    st.title(f"**{translations['IT']['select_language']}**")
    lang = st.selectbox("**Choose an option**", ["IT", "EN"])

# selezioniamo il dizionario della lingua corrente in base alla selezione dell'utente
current_lang = translations[lang]

st.title(f":blue-background[**{current_lang['welcome_title']}**]")

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

#qua andiamo a gestire il login dell'utente, usando il nostro secrets.toml per 
#eseguire accesso tramite Microsoft Azure Entra
if not st.experimental_user.is_logged_in:
    st.title("Microsoft Login:streamlit:")
    st.subheader(f":material/Login: {current_lang['login_prompt']}")
    logging.info("Launched app, waiting for the User Login.")

    if st.button(current_lang["login_button"]):
        st.login()

else:
    if st.button(current_lang["logout_button"]):
        st.logout()

    if st.experimental_user.is_logged_in:
        st.markdown(current_lang["greeting"].format(name=st.experimental_user.name, email=st.experimental_user.email))
        logging.info(f"User {st.experimental_user.name} ({st.experimental_user.email}) successfully logged in.")

    # il titolo della nostra app con qualche edit estetico
    st.markdown(f"# {current_lang['extract_data_title']}")


#la funzione per gestire il file che viene caricato, se non è vuota allora il file
#viene letto, andando a verificare però che il file sia un file pdf, ed in caso creando
#un file temporaneo per esso, in caso contrario restituisce errore, con qualche log pure
    def handle_file_upload(uploaded_file):
        if uploaded_file is not None:
            file_content = uploaded_file.read()
            file_type = uploaded_file.type
            file_extension = uploaded_file.name.split(".")[-1].lower()
            temporary_file_path = f"temp.{file_extension}"

#definiamo la funzione per i PDF, di solito i primi bytes contengono %PDF quindi ci basta questo
#per assicurarci lo sia, invece per le img, potendo avere schemi differenti, non sempre è così, quindi
#usiamo la lib Pillow e il modulo io per aprire e verificare il contenuto
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

#qua poniamo dei semplici blocchi if ed elif, affinchè se nelle nostre funzioni è presente il file_content
#allora creiamo un file temporaneo in writing-binary mode con il file_content in esso, altrimenti restituisce errore
            if file_type == "application/pdf" or file_extension == "pdf":
                if file_PDF(file_content):
                    with open(temporary_file_path, "wb") as temporary_file:
                        temporary_file.write(file_content)
                    logging.info(f"PDF file {uploaded_file.name} saved to temporary path.")
                    return temporary_file_path, file_content
                else:
                    logging.warning(f"Invalid PDF file uploaded: {uploaded_file.name}")
                    st.error(current_lang["invalid_file_error"].format(file_type="PDF", file_name=uploaded_file.name))
                    return None, None

            elif file_extension in ("jpg", "jpeg", "png"):
                if file_IMG(file_content):
                    with open(temporary_file_path, "wb") as temporary_file:
                        temporary_file.write(file_content)
                    logging.info(f"Image file {uploaded_file.name} saved to temporary path.")
                    return temporary_file_path, file_content
                else:
                    logging.warning(f"Invalid {file_extension.upper()} file uploaded: {uploaded_file.name}")
                    st.error(current_lang["invalid_file_error"].format(file_type=file_extension.upper(), file_name=uploaded_file.name))
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
    def edit_data(data):
        data_it = {}

        # questa è la nostra lista di prodotti in un dataframe, che in caso non ci sia nulla restituisci un dataframe vuoto
        # che può essere modificata
        if "Items" in data:
            if data["Items"]:
                df = pd.DataFrame(data["Items"])
            else:
                df = pd.DataFrame(columns=["Descrizione", "Codice Prodotto", "Quantità", "PrezzoUnità", "Totale"])

        edited_df = st.data_editor(df, num_rows="dynamic", key="items_df")
        lista_prodotti = edited_df.to_dict("records")

        #creiamo un form per poter modificare i dati in italiano, con i parametri che andremo ad aggiornare
        with st.form(key="edit_form"):
            data_it["Nome Venditore"] = st.text_input("Nome Venditore", value=data.get("VendorName", "N/A"), key="vendor_name")
            data_it["Indirizzo Venditore"] = st.text_input("Indirizzo Venditore", value=data.get("VendorAddress", "N/A"), key="vendor_address")
            data_it["Numero di telefono Venditore"] = st.text_input("Numero di telefono Venditore", value=data.get("MerchantPhoneNumber", "N/A"), key="vendor_phone")
            data_it["Data"] = st.text_input("Data", value=data.get("InvoiceDate", "N/A"), key="invoice_date")
            data_it["Orario"] = st.text_input("Orario", value=data.get("TransactionTime", "N/A"), key="transaction_time")
            data_it["PIVA"] = st.text_input("PIVA", value=data.get("VendorTaxId", "N/A"), key="vendor_tax_id")
            data_it["Totale"] = st.text_input("Totale", value=data.get("InvoiceTotal", "N/A"), key="invoice_total")

            #andiamo ad aprire il file temporaneo in modo tale da poterlo usare per l'ocr, usando pymupdf con tesseract integrato
            # e salvando il file in memoria, in modo tale da poterlo usare per l'ocr
            try:
                doc = pymupdf.open(temporary_file_path)
                page = doc[0]
                pix = page.get_pixmap()

                ocr_pdf_bytes = pix.pdfocr_tobytes(
                    compress=True,
                    language='eng+ita',
                    tessdata= load_dotenv("TESSDATA_PREFIX"),
                )

                ocr_doc = pymupdf.open("pdf", ocr_pdf_bytes)

            except Exception as e:
                logging.error(f"Errore durante l'OCR e la generazione del PDF: {e}")
                st.error(f"Errore durante l'OCR e la generazione del PDF: {e}")

            #andiamo ad aprire il nostro file ocr pdf, prendiamo il testo della prima pagina dai blocchi e creiamo un'immagine
            #con il pixmap, in modo tale da poter disegnare sopra l'immagine i rettangoli
            try:

                ocr_doc = pymupdf.open("pdf", ocr_pdf_bytes)
                for page_num in range(len(ocr_doc)):
                    page = ocr_doc[page_num]
                blocks = page.get_text("blocks")
                pix2 = page.get_pixmap()
                img = Image.open(io.BytesIO(pix2.tobytes("png")))
                draw = ImageDraw.Draw(img)
                #andiamo a disegnare i rettangoli sopra l'immagine, soltanto sui parametri presenti in data_it
                #e sui prodotti presenti nella lista_prodotti, in modo tale da evidenziare i dati
                for block in blocks:
                    block_text = block[4]
                    for key, value in data_it.items():
                        if value in block_text:
                            rect = pymupdf.Rect(block[:4])
                            draw.rectangle(
                                [rect.x0, rect.y0, rect.x1, rect.y1],
                                outline="red",
                                width=2
                            )

                    for item in lista_prodotti:
                        for item_key, item_value in item.items():
                            if str(item_value) in block_text:
                                rect = pymupdf.Rect(block[:4])
                                draw.rectangle(
                                    [rect.x0, rect.y0, rect.x1, rect.y1],
                                    outline="blue",
                                    width=2
                                )
                # qua mostriamo l'immagine con le aree evidenziate, e creiamo un bottone per il download
                # del file json e per aggiornare i dati, con un messaggio di successo o errore
                st.image(img, caption="PDF con aree evidenziate")

            except Exception as e:
                logging.error(f"Errore durante il disegno dei rettangoli: {e}")
                st.error(f"Errore durante il disegno dei rettangoli: {e}")

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
        #usando un try-except per gestire eventuali errori, andiamo a creare un file json usando la libreria json e buffer
        #che andremo a scrivere e scaricare, in caso di successo restituisce un messaggio di successo, altrimenti un errore
        #relativo all'aggiornamento e download del file, restituisce i dati in italiano aggiornati 
            try:
                json_string = json.dumps(json_data_italiano, indent=4, ensure_ascii=False)
                buff = BytesIO()
                buff.write(json_string.encode('utf-8'))
                buff.seek(0)

                components.html(
                    download_button(buff.getvalue(), f"{st.session_state['uploaded_file_name']}.json"),
                    height=0,
                )
                st.success(current_lang["json_success"])
                logging.info(f"JSON file {st.session_state['uploaded_file_name']}.json downloaded successfully.")

            except Exception as e:
                logging.error(f"Error during the data update and download: {e}")
                st.error(current_lang["json_error"].format(error=e))
            finally:
                doc.close()
                os.remove(temporary_file_path)
                logging.info(f"Temporary file {temporary_file_path} deleted.")

        return data_it

    #usiamo la funzione di streamlit per caricare un file pdf e consentire solo quel formato
    uploaded_file = st.file_uploader(
        label=current_lang["upload_label"], 
        type=["pdf", "jpg","png", "jpeg"],
        key="file_uploader"
        )
    logging.info("Waiting for the file upload")

    #inizializziamo le variabili di sessione che andremo ad utilizzare
    if 'extracted_data' not in st.session_state:
        st.session_state['extracted_data'] = None
    if 'uploaded_file_name' not in st.session_state:
        st.session_state['uploaded_file_name'] = None

#se il file è stato caricato con successo , gestiamo l'upload con la nostra funzione
#e creiamo un file temporaneo, che verrà aperto in formato binario e verrà letto restituendo
#estracted_data come variabile, in caso contrario restituisce un errore durante l'aalisi del documento
    if uploaded_file is not None:
        #inseriamo la variabile di sessione per l'uploaded_file in modo tale da
        #riavviare l'analisi in caso di cambio file caricato, resettando i dati estratti
        if uploaded_file.name != st.session_state['uploaded_file_name']:
            st.session_state['extracted_data'] = None  
            st.session_state['uploaded_file_name'] = uploaded_file.name

        st.success(current_lang["success_upload"].format(file_name=uploaded_file.name))
        logging.info(f"File {uploaded_file.name} uploaded successfully.")

        temporary_file_path, file_content = handle_file_upload(uploaded_file)

        if temporary_file_path:

            if st.session_state['extracted_data'] is None:
                with st.spinner(current_lang["analyzing_document"]):
                    logging.info("Analyzing the document...")
                    try:
                        with open(temporary_file_path, "rb") as f: 
                            file_content = f.read()
                            st.session_state['extracted_data'] = analyze_invoice(file_content)
                        logging.info("Document analysis completed successfully.")
                    except Exception as e:
                        logging.error(f"Error during document analysis: {e}")
                        st.error(current_lang["error_upload"].format(error=e))
                        st.session_state['extracted_data'] = None
                        logging.error("Document analysis failed.")

            #se i dati estratti sono presenti usiamo la funzione per poter permettere la 
            #modifica di essi, in caso contrario restituisce un errore di estrazione dati
            if st.session_state['extracted_data']:
                st.header(current_lang["product_list"])
                edit_data(st.session_state['extracted_data'])
            else:
                st.error(current_lang["data_extraction_error"])
                logging.error("Failed to extract data from the document.")
        else:
            logging.warning("File upload failed.")
            st.warning(current_lang["no_file_warning"])