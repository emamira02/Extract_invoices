import configparser
import base64
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

#configuriamo tutti i parametri per chiamare correttamente la nostra Azure AI, creando un file client.ini
def client():
    config = configparser.ConfigParser()
    config.read('client.ini')
    api_key = config.get('DocumentAI', 'api_key')
    endpoint = config.get('DocumentAI', 'endpoint')
    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
    return client

#qua definiamo una funzione che prende il percorso di un file come input e restituisce il contenuto del file
#codificato come una stringa base64.
def load_file_as_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    base64_bytes = base64.b64encode(data)
    base64_string = base64_bytes.decode('utf-8')
    return base64_string

#qua andiamo a definire la nostra funzione per analizzare il nostro invoice, con 
#parametro il contenuto del file, usando come modello uno preimpostato 'prebuilt-invoice',

def analyze_invoice(file_content):

    document_ai_client = client()
    model_id = 'prebuilt-invoice'

#impostiamo un try-except per gestire gli errori in caso di analisi non riuscita
#inziamo ad analizzare il nostro documento analizzando la stringa di testo creato prima
#con base64 e se i risultati sono presenti aggiungiamo i vari valori al dizionario creato
    try:
        poller = document_ai_client.begin_analyze_document(
            model_id,
            {"base64Source": file_content},
            locale="it-IT",
        )
        result = poller.result()

        if result.documents:
            document = result.documents[0]
            document_fields = document['fields']
            fields = document_fields.keys()

            data_dict = {}
            other_fields = {}  
            items_list = []

#definendo i vari parametri per andare ad estrarre correttamente tutti i vari parametri 
#che ci servono
            for field in fields:
                if field == 'Items':
                    for item in document_fields[field]['valueArray']:
                        item_fields = item['valueObject']
                        item_dict = {}

                        #essendo il modello addestrato in inglese, andiamo a prendere il valore della Description
                        #ed aggiungerlo a Descrizione,e così per ogni parametro
                        item_dict['Descrizione'] = item_fields.get('Description', {}).get('content', '')
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


            return data_dict

        else:
            print("No documents found in the result.") 
            return None

    except Exception as e:
        print(f"Error during document analysis: {e}") 
        return None
