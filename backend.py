# backend.py
import os
from dotenv import load_dotenv
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from pypdf import PdfReader
import logging
import time

load_dotenv()

AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
AZURE_DOCUMENT_INTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
# aggiungiamo un retry
MAX_RETRIES = 3
DELAY = 5  # Seconds


def analyze_receipt(pdf_file):
    """Analizza un file PDF di una ricevuta utilizzando Azure Document Intelligence."""

    credential = AzureKeyCredential(AZURE_DOCUMENT_INTELLIGENCE_KEY)
    document_intelligence_client = DocumentIntelligenceClient(
        endpoint=AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT, credential=credential
    )

    for attempt in range(MAX_RETRIES):
        try:
            # Leggi il contenuto del file PDF
            pdf_content = pdf_file.read()

            # Analizza il documento con il modello predefinito di ricevute
            poller = document_intelligence_client.begin_analyze_document(
                "prebuilt-receipt", document=pdf_content
            )
            result = poller.result()

            extracted_data = {
                "Nome Venditore": None,
                "Indirizzo Venditore": None,
                "Numero di telefono Venditore": None,
                "Data": None,
                "PIVA": None,
                "Totale": None,
                "Lista di prodotti": []
            }

            # Estrai i campi di interesse
            for field, field_value in result.documents[0].fields.items():
                if field == "MerchantName":
                    extracted_data["Nome Venditore"] = field_value.value
                elif field == "MerchantAddress":
                    extracted_data["Indirizzo Venditore"] = field_value.value
                elif field == "MerchantPhoneNumber":
                    extracted_data["Numero di telefono Venditore"] = field_value.value
                elif field == "TransactionDate":
                    extracted_data["Data"] = field_value.value
                elif field == "MerchantTaxId":
                    extracted_data["PIVA"] = field_value.value
                elif field == "Total":
                    extracted_data["Totale"] = field_value.value

            # Estrai la lista dei prodotti (Items)
            if "Items" in result.documents[0].fields:
                for item in result.documents[0].fields["Items"].value:
                    product = {
                        "Descrizione": None,
                        "Quantità": None,
                        "Costo unitario": None,
                        "Costo totale": None,
                        "Codice prodotto": None  # Potrebbe non essere sempre presente
                    }

                    if "Name" in item.value:
                        product["Descrizione"] = item.value["Name"].value
                    if "Quantity" in item.value:
                        product["Quantità"] = item.value["Quantity"].value
                    if "Price" in item.value:
                        product["Costo unitario"] = item.value["Price"].value
                    if "TotalPrice" in item.value:
                        product["Costo totale"] = item.value["TotalPrice"].value

                    extracted_data["Lista di prodotti"].append(product)

            return extracted_data

        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(DELAY)  # Wait before retrying
            else:
                logging.error(f"Extraction completely failed after {MAX_RETRIES} attempts.")
                return None

def extract_text_from_pdf(pdf_file):
    """Estrae il testo da un file PDF usando pypdf."""
    try:
        pdf_content = pdf_file.read()
        pdf_reader = PdfReader(pdf_content)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        logging.error(f"Error during text extraction: {e}")
        return None
