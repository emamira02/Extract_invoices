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
    st.markdown("# Scanner a :red[PDF] with :blue-background[Azure AI]")

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

        data["VendorName"] = st.text_input("Nome Venditore", value=data.get("VendorName", "N/A"))
        data["VendorAddress"] = st.text_input("Indirizzo Venditore", value=data.get("VendorAddress", "N/A"))
        data["Numero di telefono Venditore"] = st.text_input("Numero di telefono Venditore", value=data.get("Numero di telefono Venditore", "N/A"))
        data["InvoiceDate"] = st.text_input("Data", value=data.get("InvoiceDate", "N/A"))
        data["VendorTaxId"] = st.text_input("PIVA", value=data.get("VendorTaxId", "N/A"))
        data["InvoiceTotal"] = st.text_input("Totale", value=data.get("InvoiceTotal", "N/A"))
      

        # questa è la nostra lista di prodotti, che può essere modificata
        st.subheader("Lista di Prodotti")
        if "Items" in extracted_data:
            df = pd.DataFrame(extracted_data["Items"])

        edited_df = st.data_editor(df, num_rows="dynamic") 

        data["Lista di prodotti"] = edited_df.to_dict("records") 

        return data

    #usiamo la funzione di streamlit per caricare un file pdf e consentire solo quel formato
    uploaded_file = st.file_uploader("Carica un file PDF", type=["pdf"])

#se il file è stato caricato con successo , gestiamo l'upload con la nostra funzione
#e creiamo un file temporaneo, che verrà aperto in formato binario e verrà letto restituendo
#estracted_data come variabile, in caso contrario restituisce un errore durante l'aalisi del documento
    if uploaded_file is not None:
        st.write("File caricato con successo!")

        temporary_file_path = handle_file_upload(uploaded_file)
        if temporary_file_path:
            with st.spinner("Analizzando il documento..."):
                try:
                    with open(temporary_file_path, "rb") as f: 
                        file_content = f.read()
                        extracted_data = analyze_invoice(file_content)
                except Exception as e:
                    logging.error(f"Error during document analysis: {e}")
                    st.error(f"Error during document analysis: {e}")
                    extracted_data = None

                os.remove(temporary_file_path)  

            #se i dati estratti sono presenti usiamo la funzione per poter permettere la 
            #modifica di essi, in caso contrario restituisce un errore di estrazione dati
            if extracted_data:
                st.header("Dati Estratti")
                edited_data = edit_data(extracted_data)

                #queste due righe di codice sono per visualizzare i nostri dati json
                #in fase di debug, successivamente vanno tolte perchè non va mostrato il json
                st.subheader("Dati Editati")
                st.write(edited_data)

            #creiamo un bottone per scaricare i nostri dati in formato json
                st.download_button(
                    label="Scarica i dati in formato JSON",
                    data=json.dumps(edited_data, indent=4, ensure_ascii=False).encode('utf-8'),
                    file_name="extracted_data.json",
                    mime="application/json",
                )
            else:
                st.error("Impossibile estrarre i dati dal documento.")