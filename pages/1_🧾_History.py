import streamlit as st
import os
from database import get_crono, get_data_analysis
import sqlite3
import datetime
import pandas as pd
import json
from io import BytesIO
from PIL import Image
import pymupdf
import io
import logging
from PIL import ImageDraw
from fuzzywuzzy import fuzz
import streamlit.components.v1 as components
from backend import download_button
from frontend import translations

#andiamo a connettere il nostro database SQLite
#e a creare un cursore per eseguire le query
conn = sqlite3.connect('cronologia.db')
cursor = conn.cursor()

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

    #andiamo a creare una cartella temporanea per i file
    #che andremo a generare durante l'analisi dei documenti
    temp_files_dir = "temp_files"
    os.makedirs(temp_files_dir, exist_ok=True)


    st.title(f"📋 {current_lang.get('analysis_history', 'Analysis History')}")
    st.divider()

    #andiamo a prendere i dati dal nostro database SQLite
    #e a creare una lista con le informazioni delle analisi effettuate 
    #in modo da poterle visualizzare in un formato tabellare
    view_analysis = get_crono(cursor)

    #qua definiamo una funzione per visualizzare i dettagli dell'analisi
    def view_analysis_details(analysis_id, analysis_name, analysis_date):
        with st.dialog(f"{current_lang.get('analysis_details', 'Analysis Details')}: {analysis_name}", key=f"dialog_{analysis_id}"):
            analysis_data = get_data_analysis(cursor, analysis_id)
            
            if not analysis_data:
                st.error(current_lang.get("data_not_found", "Analysis data not found."))
                st.button(current_lang.get("close_button", "Close"), key=f"close_dialog_{analysis_id}")
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
            except Exception as e:
                st.error(current_lang.get("rectangle_error", "Error").format(error=e))
            
            #andiamo a visualizzare i dati dell'analisi in un formato tabellare
            st.subheader(current_lang.get("info_textinput", "Vendor Information"))
            vendor_info = {
                current_lang.get("text_input", ["Vendor Name"])[0]: analysis_data.get("VendorName", "N/A"),
                current_lang.get("text_input", ["", "Vendor Address"])[1]: analysis_data.get("VendorAddress", "N/A"),
                current_lang.get("text_input", ["", "", "Vendor Phone Number"])[2]: analysis_data.get("MerchantPhoneNumber", "N/A"),
                current_lang.get("text_input", ["", "", "", "Date"])[3]: analysis_data.get("InvoiceDate", "N/A"),
                current_lang.get("text_input", ["", "", "", "", "Time"])[4]: analysis_data.get("TransactionTime", "N/A"),
                current_lang.get("text_input", ["", "", "", "", "", "VAT Number"])[5]: analysis_data.get("VendorTaxId", "N/A"),
                current_lang.get("text_input", ["", "", "", "", "", "", "Total"])[6]: analysis_data.get("InvoiceTotal", "N/A")
            }
            
            for key, value in vendor_info.items():
                st.text(f"{key}: {value}")
            
            #andiamo a mettere una condizione per visualizzare i dati dell'analisi
            if "Items" in analysis_data and analysis_data["Items"]:
                st.subheader(current_lang.get("analysis_info", "Product Information"))
                items = []
                for item in analysis_data["Items"]:
                    item_dict = {}
                    for i, key in enumerate(item.keys()):
                        column_name = current_lang.get("dataframe_columns", ["Description", "Product Code", "Quantity", "Unit Price", "Total"])[min(i, 4)]
                        item_dict[column_name] = item.get(key, None)
                    items.append(item_dict)
                df = pd.DataFrame(items, columns=current_lang.get("dataframe_columns", ["Description", "Product Code", "Quantity", "Unit Price", "Total"]))
                st.dataframe(df)
            
            #poniamo un blocco try-except per gestire eventuali errori durante la visualizzazione del documento
            try:
                st.subheader(current_lang.get("extract_image", "Document with annotations"))
                if os.path.exists(temp_file_path):
                    doc = pymupdf.open(temp_file_path)
                    page = doc[0]
                    pix = page.get_pixmap()
                    
                    img_bytes = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_bytes))
                    st.image(img, width=500)
                    
                    #andiamo nel dizionario a cercare le annotazioni e a visualizzarle
                    json_data = {
                        "VendorName": analysis_data.get("VendorName", "N/A"),
                        "VendorAddress": analysis_data.get("VendorAddress", "N/A"),
                        "MerchantPhoneNumber": analysis_data.get("MerchantPhoneNumber", "N/A"),
                        "InvoiceDate": analysis_data.get("InvoiceDate", "N/A"),
                        "TransactionTime": analysis_data.get("TransactionTime", "N/A"),
                        "VendorTaxId": analysis_data.get("VendorTaxId", "N/A"),
                        "InvoiceTotal": analysis_data.get("InvoiceTotal", "N/A"),
                        "Items": analysis_data.get("Items", [])
                    }
                    
                    if st.button(current_lang.get("download_button", "Download JSON")):
                        json_string = json.dumps(json_data, indent=4, ensure_ascii=False)
                        buff = BytesIO()
                        buff.write(json_string.encode('utf-8'))
                        buff.seek(0)
                        
                        file_name = f"{analysis_name}.json"
                        download_html = download_button(buff.getvalue(), file_name)
                        components.html(download_html, height=0)
                    
            except Exception as e:
                st.error(current_lang.get("rectangle_error", "Error during image rendering: {error}").format(error=e))
            
            st.button(current_lang.get("close_button", "Close"), key=f"close_dialog_{analysis_id}")
            
            try:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except:
                pass

    #se ci sono analisi da visualizzare andiamo a creare una lista con le informazioni delle analisi effettuate
    #e a visualizzarle in un formato tabellare utilizzando la with st.container()
    if view_analysis:
        
        with st.container():
            
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
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.write(f"**{row['Name']}**")
                    
                    with col2:
                        st.write(f"📅 {row['Date']}")
                    
                    with col3:
                        if st.button(current_lang.get("view_button", "View"), key=f"view_{row['ID']}"):
                            view_analysis_details(row['ID'], row['Name'], row['Date'])
                    
                    st.divider()
    else:
        st.info(current_lang.get("no_history", "No analysis history available."))

    #chiudiamo la connessione al database
    conn.close()