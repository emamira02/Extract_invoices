import streamlit as st
import json
import logging
import pandas as pd
import os
import io
from io import BytesIO
import base64
from PIL import Image
import streamlit.components.v1 as components
from backend import analyze_invoice

# configuriamo la nostra pagina per visualizzare tutto centralmente, ed impostando il titolo
st.set_page_config(
    page_title="Data Extractor",
    layout="centered"
)

#inseriamo il logo dell'azienda nella nostra app
st.logo("https://www.oaks.cloud/_next/static/media/oaks.13e2f970.svg",
        size="large",
        link="https://www.oaks.cloud/")

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
    st.subheader(":material/Login: Please log in to continue")
    logging.info("Launched app, waiting for the User Login.")

    if st.button("Log in"):
        st.login()

else:
    if st.button("Log out"):
        st.logout()

    if st.experimental_user.is_logged_in:
        st.markdown(f"Hello, **{st.experimental_user.name}**, {st.experimental_user.email}")
        logging.info(f"User {st.experimental_user.name} ({st.experimental_user.email}) successfully logged in.")

    # il titolo della nostra app con qualche edit estetico
    st.markdown("# Extract :blue[Data] with :blue-background[Azure AI]")

    def download_button(object_to_download, download_filename):
        #con un try-except andiamo a gestire il download del file, se è un dataframe
        #lo convertiamo in csv, altrimenti se è un byte lo codifichiamo in base64 e lo convertiamo in stringa
        try:
            if isinstance(object_to_download, pd.DataFrame):
                object_to_download = object_to_download.to_csv(index=False)
            elif isinstance(object_to_download, bytes):
                #qui andiamo a codificare l'oggetto in base64 e lo convertiamo in stringa per il download, che verrà
                #eseguito tramite un link html che verrà cliccato automaticamente per scaricare il file, altrimenti
                #restituisce un errore di download del file con un messaggio di errore e un log di errore 
                b64 = base64.b64encode(object_to_download).decode()
            else:
                object_to_download = json.dumps(object_to_download, indent=4, ensure_ascii=False)
                b64 = base64.b64encode(object_to_download.encode()).decode()

            dl_link = f"""
            <html>
            <head>
            <title>Start Auto Download file</title>
            <script src="http://code.jquery.com/jquery-3.2.1.min.js"></script>
            <script>
            $('<a href="data:application/json;base64,{b64}" download="{download_filename}">')[0].click()
            </script>
            </head>
            </html>
            """
            return dl_link
        except Exception as e:
            logging.error(f"Errore nella creazione del link di download: {e}")
            st.error(f"Errore nella creazione del link di download: {e}")
            return None

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
                    return temporary_file_path
                else:
                    logging.warning(f"Invalid PDF file uploaded: {uploaded_file.name}")
                    st.error(f"Invalid PDF file uploaded: {uploaded_file.name}")
                    return None

            elif file_extension in ("jpg", "jpeg", "png"):
                if file_IMG(file_content):
                    with open(temporary_file_path, "wb") as temporary_file:
                        temporary_file.write(file_content)
                    return temporary_file_path
                else:
                    logging.warning(f"Invalid {file_extension.upper()} file uploaded: {uploaded_file.name}")
                    st.error(f"Invalid {file_extension.upper()} file uploaded: {uploaded_file.name}")
                    return None

            else:
                logging.warning(f"Unsupported file type uploaded: {file_type} - {uploaded_file.name}")
                st.error(f"Unsupported file type uploaded: {uploaded_file.name}")
                return None
        else:
            logging.warning("There's no file uploaded, please follow the right instructions")
            st.warning("There's no file uploaded, please follow the right instructions")
            return None

#definiamo una funziona avente come parametro i nostri dati
    def edit_data(data):

#per mostrare solo i dati in italiano creiamo un dizionario al quale aggiungeremo tutti i parametri
        data_it = {}

        # questa è la nostra lista di prodotti in un dataframe, che in caso non ci sia nulla restituisci un dataframe vuoto
        # che può essere modificata
        st.subheader("Lista di Prodotti")
        if "Items" in data:
            df = pd.DataFrame(data["Items"])
        else:
            df = pd.DataFrame()

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

            submit_button = st.form_submit_button(label="Aggiorna e Scarica Dati")

        if submit_button:
            #aggiorniamo i dati in italiano e creiamo un file json con essi per il download 
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
                    download_button(buff.getvalue(), f"{st.session_state['uploaded_file_name']}_italiano.json"),
                    height=0,
                )
                st.success("Dati aggiornati e file JSON scaricato con successo!")

            except Exception as e:
                logging.error(f"Errore durante l'aggiornamento dei dati e il download: {e}")
                st.error(f"Errore durante l'aggiornamento dei dati e il download: {e}")

        return data_it

    #usiamo la funzione di streamlit per caricare un file pdf e consentire solo quel formato
    uploaded_file = st.file_uploader(
        label = "Upload an Invoice or a Receipt", 
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

        st.success(f"File {uploaded_file.name} caricato con successo")

        temporary_file_path = handle_file_upload(uploaded_file)
        if temporary_file_path:
            if st.session_state['extracted_data'] is None:
                with st.spinner("Analizzando il documento..."):
                    try:
                        with open(temporary_file_path, "rb") as f: 
                            file_content = f.read()
                            st.session_state['extracted_data'] = analyze_invoice(file_content)
                    except Exception as e:
                        logging.error(f"Error during document analysis: {e}")
                        st.error(f"Error during document analysis: {e}")
                        st.session_state['extracted_data'] = None

            #se i dati estratti sono presenti usiamo la funzione per poter permettere la 
            #modifica di essi, in caso contrario restituisce un errore di estrazione dati
            if st.session_state['extracted_data']:
                st.header("Dati Estratti")
                edit_data(st.session_state['extracted_data'])
            else:
                st.error("Impossibile estrarre i dati dal documento.")