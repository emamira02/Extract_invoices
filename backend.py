import os 
from pypdf import PdfReader
import logging
import time
import streamlit as st

#definiamo una funzione che contiene il file_content
def file_PDF(file_content):
            return file_content.startswith(b'%PDF',)


# Con questa funzione andiamo a leggere il pdf e ad estrarre il testo
# in caso di errore ci restituisce un errore
def read_pdf_and_extract_text(temporary_file_path, summarize_all, selected_page):
    try:
        pdf_reader = PdfReader(temporary_file_path)
        if summarize_all:
            extracted_text = "\n".join([pdf_reader.pages[i].extract_text() for i in range(len(pdf_reader.pages))])
        else:
            extracted_text = pdf_reader.pages[selected_page].extract_text()
        return extracted_text
    except Exception as e:
        raise Exception(f"Error reading PDF: {e}")
