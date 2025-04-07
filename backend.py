import configparser
import base64
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
import logging
import json
import base64
import pandas as pd
import streamlit as st
import sqlite3

# configuriamo tutti i parametri per chiamare correttamente la nostra Azure AI, creando un file client.ini
def client():
    config = configparser.ConfigParser()
    config.read('client.ini')
    api_key = config.get('DocumentAI', 'api_key')
    endpoint = config.get('DocumentAI', 'endpoint')
    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
    return client


def create_database():
    #creiamo il nostro database SQLite e la tabella per memorizzare i dati estratti
    conn = sqlite3.connect('invoice_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_name TEXT,
            field_value TEXT
        )
    ''')
    if not cursor.fetchone():
        cursor.execute('''CREATE TABLE invoice_data
                          (field_name text, field_value text)''')
        conn.commit()
    conn.close()

def insert_data_to_db(data_dict):
    #inseriamo i dati estratti nel database SQLite
    conn = sqlite3.connect('invoice_data.db')
    cursor = conn.cursor()
    
    #per ogni campo del nostro dizionario andiamo ad inserire il valore e il nome del campo
    for field_name, field_value in data_dict.items():
        cursor.execute('''
            INSERT INTO invoice_data (field_name, field_value) VALUES (?, ?)
        ''', (field_name, field_value))
    
    conn.commit()
    conn.close()


def update_data_to_db(data_dict):
    #aggiorniamo i dati estratti nel database SQLite
    conn = sqlite3.connect('invoice_data.db')
    cursor = conn.cursor()
    
    #per ogni campo del nostro dizionario andiamo ad aggiornare il valore e il nome del campo
    for field_name, field_value in data_dict.items():
        cursor.execute('''
            UPDATE invoice_data SET field_value = ? WHERE field_name = ?
        ''', (field_value, field_name))
    
    conn.commit()
    conn.close()

def view_data_from_db():
    # Ensure the database and table exist before fetching data
    conn = sqlite3.connect('invoice_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_name TEXT,
            field_value TEXT
        )
    ''')
    
    cursor.execute('''
        SELECT * FROM invoice_data
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    return rows


#qua andiamo a definire la nostra funzione per analizzare il nostro invoice, con 
#parametro il contenuto del file, usando come modello uno preimpostato 'prebuilt-invoice',

@st.cache_data(ttl=12*3600)
def analyze_invoice(file_content):

    invoice_ai_client = client()
    model_id = 'prebuilt-invoice'
    data_dict = {}

#impostiamo un try-except per gestire gli errori in caso di analisi non riuscita
#inziamo ad analizzare il nostro documento analizzando la stringa di testo creato prima
#con base64 e se i risultati sono presenti aggiungiamo i vari valori al dizionario creato
    try:
        poller = invoice_ai_client.begin_analyze_document(
            model_id,
            {"base64Source": file_content},
            locale="it-IT",
        )
        result = poller.result()

        if result.documents:
            document = result.documents[0]
            document_fields = document['fields']
            fields = document_fields.keys()

            other_fields = {}  
            items_list = []

#definendo i vari parametri per andare ad estrarre correttamente tutti i vari parametri 
#che ci servono
            for field in fields:
                if field == 'Items':
                    for item in document_fields[field]['valueArray']:
                        item_fields = item.get('valueObject', {})
                        item_dict = {}

                        #essendo il modello addestrato in inglese, andiamo a prendere il valore della Description
                        #ed aggiungerlo a Descrizione,e così per ogni parametro
                        item_dict['Descrizione'] = item_fields.get('Description', {}).get('content', '')
                        item_dict['Codice Prodotto'] = item_fields.get('ProductCode', {}).get('content', '')
                        item_dict['Quantità'] = item_fields.get('Quantity', {}).get('content', '')
                        item_dict['PrezzoUnità'] = item_fields.get('UnitPrice', {}).get('content', '')
                        item_dict['Totale'] = item_fields.get('Amount', {}).get('content', '')
                        
                        #poniamo la condizione per la quale se la quantità è vuota o None
                        #allora assegniamo direttamente il valore 1, se la quantità è 1 allora il prezzo
                        #di ciascuna unità corrisponde al totale, in caso contrario fa una divisione
                        #tra totale e prezzo unità
                        if not item_dict['Quantità']: 
                            item_dict['Quantità'] = "1" 
                        if item_dict['Quantità'] == "1": 
                            item_dict['PrezzoUnità'] = item_dict['Totale']
                        else:
                            try:
                                totale = item_dict['Totale'].strip()
                                prezzo_unitario = item_dict['PrezzoUnità'].strip()
                                item_dict['PrezzoUnità'] = float(totale) / float(prezzo_unitario)
                            except (ValueError, TypeError):
                                None

                              
                            
                        items_list.append(item_dict)
                    continue

            #in caso ci siano altri valori da aggiungere li aggiungiamo al dizionario creato
                value = document_fields[field].get('content', '')
                other_fields[field] = value


            #aggiorniamo il nostro dizionario principale facendo un "merge" tra i due
            #e lo restituiamo
            data_dict.update(other_fields)
            data_dict['Items'] = items_list

            # aggiungiamo un blocco try affinchè, ci estragga il numero di telefono e orario dal receipt model
            #poichè non presente nel prebuilt-invoice model e li aggiungiamo al dict
            try:
                receipt_data = analyze_receipt(file_content)
                if receipt_data:
                    phone_number, tran_time = receipt_data
                    data_dict["MerchantPhoneNumber"] = phone_number
                    data_dict["TransactionTime"] = tran_time
            except Exception as e:
                logging.warning(f"Failed to extract phone number or transaction time from receipt: {e}")


            return data_dict

        else:
            print("No documents found in the result.") 
            return None

    except Exception as e:
        print(f"Error during document analysis: {e}") 
        return None

@st.cache_data(ttl=12*3600)
def analyze_receipt(file_content):

    receipt_ai_client = client()
    model_id2 = 'prebuilt-receipt'


    try:
        poller = receipt_ai_client.begin_analyze_document(
            model_id2,
            {"base64Source": file_content},
            locale="it-IT",
        )
        result = poller.result()

        if result.documents:
            document = result.documents[0]
            #poniamo una condizione per il quale, se questi campi si trovano nel documento, li estraiamo 
            #e li restituiamo per mostrarli, in caso contrario non restituisce nulla
            if 'MerchantPhoneNumber' in document['fields'] and 'TransactionTime' in document['fields']:
                phone_number = document['fields']['MerchantPhoneNumber'].get('content', None)
                tran_time = document['fields']['TransactionTime'].get('content', None)
                return phone_number, tran_time
            else:
                logging.info("MerchantPhoneNumber or TransactionTime field not found in receipt.")
                return None  
        else:
            logging.info("No documents found in receipt analysis.")
            return None

    except Exception as e:
        logging.error(f"Error during receipt analysis: {e}")
        return None

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