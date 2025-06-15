import base64
import pandas as pd
import json
import logging

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
        logging.info(f"Download link created for {download_filename}")
        return dl_link
    except Exception as e:
        logging.error(f"Errore nella creazione del link di download: {e}")
        #st.error(f"Errore nella creazione del link di download: {e}")
        return None