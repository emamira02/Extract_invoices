import configparser
import base64
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
import logging
import json
import base64
import pandas as pd
import streamlit as st
import io
from PIL import Image, ImageDraw
import pymupdf

# configuriamo tutti i parametri per chiamare correttamente la nostra Azure AI, creando un file client.ini
def client():
    config = configparser.ConfigParser()
    config.read('client.ini')
    api_key = config.get('DocumentAI', 'api_key')
    endpoint = config.get('DocumentAI', 'endpoint')
    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
    return client

#qua andiamo a definire la nostra funzione per analizzare il nostro invoice, con 
#parametro il contenuto del file, usando come modello uno preimpostato 'prebuilt-invoice',

@st.cache_data(show_spinner=False)
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
            {"base64Source": base64.b64encode(file_content).decode("utf-8")},
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

            #richiamiamo la funzione per estrarre i poligoni
            #e li aggiungiamo al nostro dizionario
            polygons = extract_polygons(result)
            data_dict['polygons'] = polygons

            # aggiungiamo un blocco try affinchè, ci estragga il numero di telefono e orario dal receipt model
            #poichè non presente nel prebuilt-invoice model e li aggiungiamo al dict
            try:
                receipt_data = analyze_receipt(file_content)
                if receipt_data:
                    phone_number, tran_time, receipt_polygons = receipt_data
                    data_dict["MerchantPhoneNumber"] = phone_number
                    data_dict["TransactionTime"] = tran_time
                    
                    #in caso ci siano poligoni estratti dal receipt, quindi in caso siano presenti il numero di telefono
                    #e l'orario, li andiamo ad aggiungere insieme a quelli estratti prima
                    if receipt_polygons:
                        data_dict['polygons'].update(receipt_polygons)
            except Exception as e:
                logging.warning(f"Failed to extract phone number or transaction time from receipt: {e}")


            return data_dict

        else:
            print("No documents found in the result.") 
            return None

    except Exception as e:
        print(f"Error during document analysis: {e}") 
        return None
#definiamo la funzione per estrarre i poligoni, che andrà a prendere i poligoni
#dai vari campi e a salvarli in un dizionario, in modo da poterli usare per disegnare
def extract_polygons(result):

    polygons = {}
    target_fields = {"VendorName", "VendorAddress", "VendorTaxId", "InvoiceDate", "InvoiceTotal", "AmountDue"}
    
    for document in result.documents:
        for field_name, field in document.fields.items():
            if field_name == "Items":
               #iteriamo su ogni elemento della lista Items per ogni campo per andare a prendere i poligoni
                for index, item in enumerate(field.value_array):
                    for subfield_name, subfield in item.value_object.items():
                        if subfield.bounding_regions:
                            for region in subfield.bounding_regions:
                                key = f"Items[{index}] {subfield_name}"
                                if key not in polygons:
                                    # andiamo a salvare il poligono per ogni subfield 
                                    polygons[key] = region.polygon
            else:
                if field.bounding_regions and field_name in target_fields:
                    #andiamo a salvare il poligono per ogni campo affinchè
                    #possa essere disegnato sull'immagine e restituiamo la nostra variabile
                    polygons[field_name] = field.bounding_regions[0].polygon
    
    return polygons

@st.cache_data(show_spinner=False)
def analyze_receipt(file_content):

    receipt_ai_client = client()
    model_id2 = 'prebuilt-receipt'


    try:
        poller = receipt_ai_client.begin_analyze_document(
            model_id2,
            {"base64Source": base64.b64encode(file_content).decode("utf-8")},
            locale="it-IT",
        )
        result = poller.result()
        polygons = {}
        receipt_fields = {"MerchantPhoneNumber", "TransactionTime"}
        #poniamo una condizione per il quale, se questi campi si trovano nel documento, li estraiamo 
        #e li restituiamo per mostrarli, in caso contrario non restituisce nulla
        if result.documents:
            document = result.documents[0]
            phone_number = None
            tran_time = None
            
            for field_name, field in document['fields'].items():
                if field_name in receipt_fields:
                    if field_name == 'MerchantPhoneNumber':
                        phone_number = field.get('content', None)
                    elif field_name == 'TransactionTime':
                        tran_time = field.get('content', None)
                    
                    #salviamo i poligoni per ogni campo in modo che essi possano essere aggiunti ai precedenti
                    #e disegnati sull'immagine
                    if field.get('boundingRegions'):
                        polygon = field['boundingRegions'][0]['polygon']
                        polygons[field_name] = polygon
            
            return phone_number, tran_time, polygons
        else:
            logging.info("No documents found in receipt analysis.")
            return None, None, None

    except Exception as e:
        logging.error(f"Error during receipt analysis: {e}")
        return None, None, None
#definiamo la funzione per creare l'immagine annotata, che andrà a prendere il file
#e i poligoni estratti in precedenza e a disegnarli sull'immagine
def create_annotated_image(file_content, polygons):

    try:
        #se il file è un pdf andiamo a calcolare la scala per il ridimensionamento
        #dell'immagine in base alla dimensione della pagina
        is_pdf = file_content.startswith(b'%PDF')
        
        if is_pdf:
            #grazie a pymupdf andiamo ad aprire il file e a prendere la prima pagina
            # e a convertirla in un'immagine 
            doc = pymupdf.open(stream=file_content, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap()
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            
            #andiamo a calcolare la scala per il ridimensionamento
            #dell'immagine in base alla dimensione della pagina
            expected_width = (page.rect.width / 72) * 96
            expected_height = (page.rect.height / 72) * 96
            scale_x = image.width / expected_width
            scale_y = image.height / expected_height
        else:
            #andiamo a convertire il file in un'immagine
            image = Image.open(io.BytesIO(file_content)).convert("RGB")
            scale_x = scale_y = 1.0
        
        # definiamo un dict per i colori dei vari campi
        # in modo da poterli cambiare in base al campo
        colors = {
            "VendorName": "red",
            "VendorAddress": "blue",
            "MerchantPhoneNumber": "green",
            "InvoiceDate": "orange",
            "TransactionTime": "purple",
            "VendorTaxId": "brown",
            "InvoiceTotal": "grey",
            "AmountDue": "red"
        }
        
        draw = ImageDraw.Draw(image)
        
        # estraiamo i punti dal poligono e andiamo a calcolare il bounding box per ogni poligono
        # e a disegnarli sull'immagine
        for field_name, polygon in polygons.items():

            if hasattr(polygon[0], "x"):
                points = [(point.x * 96 * scale_x, point.y * 96 * scale_y) for point in polygon]
            else:
                pts = list(zip(polygon[0::2], polygon[1::2]))
                points = [(p[0] * 96 * scale_x, p[1] * 96 * scale_y) for p in pts]
            
            # segniamo i punti usando le coordinate calcolate, imponiamo un margine
            # per il bounding box in modo da non farlo coincidere con i punti
            margin = 5
            min_x = min(p[0] for p in points) - margin
            min_y = min(p[1] for p in points) - margin
            max_x = max(p[0] for p in points) + margin
            max_y = max(p[1] for p in points) + margin
            
            #qui invece andiamo a disegnare il bounding box
            #e a colorarlo in base al campo
            color = colors.get(field_name.split(" ")[0] if " " in field_name else field_name, "red")
            draw.rectangle([min_x, min_y, max_x, max_y], outline=color, width=2)
        
        #convertiamo l'immagine in un oggetto bytes
        #in modo da poterla scaricare direttamente
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr.getvalue()
    
    except Exception as e:
        logging.error(f"Error creating annotated image: {e}")
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