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

def analyze_invoice(file_content):

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

            data_dict = {}
            other_fields = {}  # Store non-item fields
            items_list = []

            for field in fields:
                if field == 'Items':
                    for item in document_fields[field]['valueArray']:
                        item_fields = item['valueObject']
                        item_dict = {}

                        # Extract fields with error handling
                        item_dict['Description'] = item_fields.get('Description', {}).get('content', '')
                        item_dict['Quantity'] = item_fields.get('Quantity', {}).get('content', '')
                        item_dict['UnitPrice'] = item_fields.get('UnitPrice', {}).get('content', '')
                        item_dict['Amount'] = item_fields.get('Amount', {}).get('content', '')

                        items_list.append(item_dict)
                    continue

                # Store other fields
                value = document_fields[field].get('content', '')
                other_fields[field] = value


            # Merge dictionaries, putting other fields first, and Items last
            data_dict.update(other_fields)
            data_dict['Items'] = items_list


            return data_dict

        else:
            print("No documents found in the result.")  # Log to console, not Streamlit
            return None

    except Exception as e:
        print(f"Error during document analysis: {e}")  # Log to console, not Streamlit
        return None
