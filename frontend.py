import streamlit as st
import json
import logging
import pandas as pd
import os
from backend import analyze_invoice

# configuriamo la nostra pagina per visualizzare tutto centralmente, ed impostando il titolo
st.set_page_config(
    page_title="Receipt Extractor",
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
    st.markdown("# Extract Invoice Data from a :red[PDF] with :blue-background[Azure AI]")

#la funzione per gestire il file che viene caricato, se non è vuota allora il file
#viene letto, andando a verificare però che il file sia un file pdf, ed in caso creando
#un file temporaneo per esso, in caso contrario restituisce errore, con qualche log pure
    def handle_file_upload(uploaded_file):
        if uploaded_file is not None:
            file_content = uploaded_file.read()
            file_type = uploaded_file.type
            file_extension = uploaded_file.name.split(".")[-1].lower()
            temporary_file_path = "temp.pdf"

            def file_PDF(file_content):
                return file_content.startswith(b'%PDF',)

            if file_type == "application/pdf" or file_extension == "pdf":
                if file_PDF(file_content):
                    with open(temporary_file_path, "wb") as temporary_file:
                        temporary_file.write(file_content)
                    return temporary_file_path
                else:
                    logging.warning(f"Invalid PDF file uploaded: {uploaded_file.name}")
                    st.error(f"Invalid PDF file uploaded: {uploaded_file.name}")
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

        data_it["Nome Venditore"] = st.text_input("Nome Venditore", value=data.get("VendorName", "N/A"), key="vendor_name")
        data_it["Indirizzo Venditore"] = st.text_input("Indirizzo Venditore", value=data.get("VendorAddress", "N/A"), key="vendor_address")
        data_it["Numero di telefono Venditore"] = st.text_input("Numero di telefono Venditore", value=data.get("VendorPhoneNumber", "N/A"), key="vendor_phone")
        data_it["Data"] = st.text_input("Data", value=data.get("InvoiceDate", "N/A"), key="invoice_date")
        data_it["PIVA"] = st.text_input("PIVA", value=data.get("VendorTaxId", "N/A"), key="vendor_tax_id")
        data_it["Totale"] = st.text_input("Totale", value=data.get("InvoiceTotal", "N/A"), key="invoice_total")
      

        # questa è la nostra lista di prodotti in un dataframe, che in caso non ci sia nulla restituisci un dataframe vuoto
        # che può essere modificata
        st.subheader("Lista di Prodotti")
        if "Items" in data:
            df = pd.DataFrame(data["Items"])
        else:
            df = pd.DataFrame()

        edited_df = st.data_editor(df, num_rows="dynamic", key="items_df") 

        data_it["Lista Prodotti"] = edited_df.to_dict("records")

        return data_it

    #usiamo la funzione di streamlit per caricare un file pdf e consentire solo quel formato
    uploaded_file = st.file_uploader(
        label = "Upload a PDF Invoice File", 
        type=["pdf"]
        )
    logging.info("Waiting for the file upload")

    # Initialize session state
    if 'extracted_data' not in st.session_state:
        st.session_state['extracted_data'] = None
    if 'edited_data' not in st.session_state:
         st.session_state['edited_data'] = None


#se il file è stato caricato con successo , gestiamo l'upload con la nostra funzione
#e creiamo un file temporaneo, che verrà aperto in formato binario e verrà letto restituendo
#estracted_data come variabile, in caso contrario restituisce un errore durante l'aalisi del documento
    if uploaded_file is not None:
        st.success(f"File {uploaded_file.name} caricato con successo")

        temporary_file_path = handle_file_upload(uploaded_file)
        if temporary_file_path:
            if st.session_state['extracted_data'] is None:  # Analyze only once
                with st.spinner("Analizzando il documento..."):
                    try:
                        with open(temporary_file_path, "rb") as f: 
                            file_content = f.read()
                            st.session_state['extracted_data'] = analyze_invoice(file_content)
                    except Exception as e:
                        logging.error(f"Error during document analysis: {e}")
                        st.error(f"Error during document analysis: {e}")
                        st.session_state['extracted_data'] = None

                    os.remove(temporary_file_path)  

            #se i dati estratti sono presenti usiamo la funzione per poter permettere la 
            #modifica di essi, in caso contrario restituisce un errore di estrazione dati
            if st.session_state['extracted_data']:
                st.header("Dati Estratti")
                st.session_state['edited_data'] = edit_data(st.session_state['extracted_data'])

               

            #creiamo un bottone per scaricare i nostri dati in formato json
                st.download_button(
                    label="Scarica i dati in formato JSON",
                    data=json.dumps(st.session_state['edited_data'], indent=4, ensure_ascii=False).encode('utf-8'),
                    file_name="extracted_data.json",
                    mime="application/json",
                )
            else:
                st.error("Impossibile estrarre i dati dal documento.")