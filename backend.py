import os
import configparser
import base64
from urllib.parse import urlparse
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

def client():
    config = configparser.ConfigParser()
    config.read('client.ini')
    api_key = config.get('DocumentAI', 'api_key')
    endpoint = config.get('DocumentAI', 'endpoint')
    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
    return client

def is_file_or_url(input_string):
    if os.path.isfile(input_string):
        return 'file'
    elif urlparse(input_string).scheme in ['http', 'https']:
        return 'url'
    else:
        return 'unknown'

def load_file_as_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    base64_bytes = base64.b64encode(data)
    base64_string = base64_bytes.decode('utf-8')
    return base64_string

def analyze_receipt(file_content):
    """
    Analizza un invoice utilizzando Azure Document Intelligence.
    file_content: contenuto del file in formato base64.
    Returns: A dictionary containing the extracted data, or None on error.
    """
    document_ai_client = client()
    model_id = 'prebuilt-invoice'

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

            data_dict = {
                "Nome Venditore": "N/A",
                "Indirizzo Venditore": "N/A",
                "Numero di telefono Venditore": "N/A",
                "Data": "N/A",  # Gestisce data e ora
                "PIVA": "N/A",
                "Totale": "N/A",
                "Lista di prodotti": []
            }

            for field in fields:
                if field == 'Lista di prodotti':
                    items_list = []
                    items = document_fields[field]

                    for item in items['valueArray']:
                        item_fields = item['valueObject']
                        item_dict = {
                            "Descrizione": "N/A",
                            "Quantità": "N/A",
                            "Costo unitario": "N/A",
                            "Costo totale": "N/A",
                            "Codice prodotto": "N/A"
                        }
                        for item_field in item_fields.keys():
                            value = item_fields[item_field].get('content', 'N/A')
                            item_dict[item_field] = value
                        items_list.append(item_dict)

                    data_dict['Lista di prodotti'] = items_list
                    continue  # Skip direct printing here

                value = document_fields[field].get('content', 'N/A')
                if field == "MerchantName":
                    data_dict["Nome Venditore"] = value
                elif field == "MerchantAddress":
                    data_dict["Indirizzo Venditore"] = value
                elif field == "MerchantPhoneNumber":
                    data_dict["Numero di telefono Venditore"] = value
                elif field == "TransactionDate":
                    data_dict["Data"] = value #prende data e ora se presente
                elif field == "MerchantTaxId":
                    data_dict["PIVA"] = value
                elif field == "Total":
                    data_dict["Totale"] = value


            return data_dict

        else:
            print("No documents found in the result.")  # Log to console, not Streamlit
            return None

    except Exception as e:
        print(f"Error during document analysis: {e}")  # Log to console, not Streamlit
        return None

