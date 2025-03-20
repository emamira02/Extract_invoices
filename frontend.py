import streamlit as st
import json
import logging
import pandas as pd
import os
from backend import analyze_receipt

# Configurazione della pagina
st.set_page_config(
    page_title="Receipt Extractor",
    layout="centered"
)

# Configurazione dei log
logging.basicConfig(
    filename="app.log",  # Commentare questa riga per inviare i log a stdout (per Docker)
    encoding="utf-8",
    filemode="a",       # Questa riga aggiunge i vecchi log ai nuovi, append mode
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
    level=logging.INFO
)

# Gestione del login dell'utente (se abilitato)
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

    # Titolo dell'app
    st.markdown("# Scanner a :red[PDF] with :blue-background[Azure AI]")

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


    def edit_data(data):
        """Visualizza e permette di editare i dati estratti."""

        # Campi singoli
        data["Nome Venditore"] = st.text_input("Nome Venditore", value=data.get("Nome Venditore", "N/A"))
        data["Indirizzo Venditore"] = st.text_input("Indirizzo Venditore", value=data.get("Indirizzo Venditore", "N/A"))
        data["Numero di telefono Venditore"] = st.text_input("Numero di telefono Venditore", value=data.get("Numero di telefono Venditore", "N/A"))
        data["Data"] = st.text_input("Data", value=data.get("Data", "N/A"))
        data["PIVA"] = st.text_input("PIVA", value=data.get("PIVA", "N/A"))
        data["Totale"] = st.text_input("Totale", value=data.get("Totale", "N/A"))

        # Lista di prodotti (visualizzata come tabella editabile)
        st.subheader("Lista di Prodotti")
        df = pd.DataFrame(data.get("Lista di prodotti", [])) # Handle case where 'Lista di prodotti' is missing

        # Assicurati che le colonne siano presenti anche se la lista è vuota
        if df.empty:
            df = pd.DataFrame({
                "Descrizione": ["N/A"],
                "Quantità": ["N/A"],
                "Costo unitario": ["N/A"],
                "Costo totale": ["N/A"],
                "Codice prodotto": ["N/A"]
            })

        edited_df = st.data_editor(df, num_rows="dynamic")  # Mostra come tabella editabile

        data["Lista di prodotti"] = edited_df.to_dict("records")  # Aggiorna i dati con le modifiche

        return data

    # Directly execute the code that was inside main()
    uploaded_file = st.file_uploader("Carica un file PDF", type=["pdf"])

    if uploaded_file is not None:
        st.write("File caricato con successo!")

        temporary_file_path = handle_file_upload(uploaded_file)
        if temporary_file_path:
            with st.spinner("Analizzando il documento..."):
                try:
                    with open(temporary_file_path, "rb") as f:  # Open the file in binary read mode
                        file_content = f.read()
                        extracted_data = analyze_receipt(file_content)
                except Exception as e:
                    logging.error(f"Error during document analysis: {e}")
                    st.error(f"Error during document analysis: {e}")
                    extracted_data = None

                os.remove(temporary_file_path)  # Clean up the temporary file

            if extracted_data:
                st.header("Dati Estratti")

                # Visualizza i dati estratti in forma editabile
                edited_data = edit_data(extracted_data)

                # Visualizza i dati editati
                st.subheader("Dati Editati")
                st.write(edited_data)

                # Scarica i dati in formato JSON
                st.download_button(
                    label="Scarica i dati in formato JSON",
                    data=json.dumps(edited_data, indent=4, ensure_ascii=False).encode('utf-8'),
                    file_name="extracted_data.json",
                    mime="application/json",
                )
            else:
                st.error("Impossibile estrarre i dati dal documento.")