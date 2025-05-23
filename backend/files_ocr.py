from PIL import Image
import logging
import pymupdf
import io
import os
import streamlit as st
from backend.lang import set_language



def temp_files_direct():
    #andiamo a caricare i nostri file temporanei in una cartella specifica
    temp_files_dir = "temp_files"
    os.makedirs(temp_files_dir, exist_ok=True)
    return temp_files_dir

def handle_file_upload(uploaded_file):
    current_lang = set_language()
    if uploaded_file is not None:
        file_content = uploaded_file.read()
        file_type = uploaded_file.type
        file_extension = uploaded_file.name.split(".")[-1].lower()
        is_image = file_extension in ("jpg", "jpeg", "png")

#definiamo la funzione per i PDF, di solito i primi bytes contengono %PDF quindi ci basta questo
#per assicurarci lo sia, invece per le img, potendo avere schemi differenti, non sempre è così, quindi
#usiamo la lib Pillow e il modulo io per aprire e verificare il contenuto
        temporary_file_path = os.path.join(temp_files_direct(), "temp.pdf")

        def file_PDF(file_content):
            return file_content.startswith(b'%PDF')

        def file_IMG(file_content):
            try:

                img = Image.open(io.BytesIO(file_content))
                img.verify() 
                return True
            except Exception as e:
                logging.warning(f"Invalid image file: {e}")
                return False
        #qua poniamo una condizione per verificare se il file è un immagine ed esiste, allora andiamo a 
        #creare un file temporaneo in pdf, in caso contrario andiamo a verificare se è un pdf
        if is_image and file_IMG(file_content):
            try:
                #andiamo a aprire il nostro file content e lo mettiamo in una variabile
                img = Image.open(io.BytesIO(file_content))
                
                doc = pymupdf.open()
                page = doc.new_page(width=img.width, height=img.height)
                
                #qua andiamo a convertire l'immagine in bytes 
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                img_bytes.seek(0)
                
                #qua aggiungiamo l'immagine alla pagina PDF ed infine lo salviamo in un file temporaneo
                page.insert_image(page.rect, stream=img_bytes.getvalue())
                doc.save(temporary_file_path)
                doc.close()
                
                #andiamo a leggere il file temporaneo in formato binario
                with open(temporary_file_path, "rb") as pdf_file:
                    pdf_content = pdf_file.read()
                
                logging.info(f"Image file {uploaded_file.name} converted to PDF and saved to temporary path.")
                return temporary_file_path, pdf_content
                
            except Exception as e:
                logging.error(f"Error converting image to PDF: {e}")
                st.error(f"Error processing image: {e}")
                return None, None
        
        #in caso non sia un immagine andiamo a verificare se è un pdf, in caso contrario restituiamo errore
        elif file_type == "application/pdf" or file_extension == "pdf":
            if file_PDF(file_content):
                with open(temporary_file_path, "wb") as temporary_file:
                    temporary_file.write(file_content)
                logging.info(f"PDF file {uploaded_file.name} saved to temporary path.")
                return temporary_file_path, file_content
            else:
                logging.warning(f"Invalid PDF file uploaded: {uploaded_file.name}")
                st.error(current_lang["invalid_file_error"].format(file_type="PDF", file_name=uploaded_file.name))
                return None, None
        else:
            logging.warning(f"Unsupported file type uploaded: {file_type} - {uploaded_file.name}")
            st.error(current_lang["unsupported_file_error"].format(file_name=uploaded_file.name))
            return None, None
    else:
        logging.warning("There's no file uploaded, please follow the right instructions")
        st.warning(current_lang["no_file_warning"])
        return None, None
    
def try_ocr(temporary_file_path):
    doc = pymupdf.open(temporary_file_path)
    page = doc[0]
    pix = page.get_pixmap(alpha=False)
    
    #andiamo a creare un’immagine a partire dai dati del pixmap, salvata in un buffer 
    # di memoria e poi la memorizziamo nella session state
    img_bytes_original = io.BytesIO()
    img_original = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img_original.save(img_bytes_original, format='PNG')
    img_bytes_original.seek(0)
    st.session_state['original_image'] = img_bytes_original.getvalue()
    
    #andiamo a memorizzare le dimensioni del documento nella session state
    #per poterle usare in seguito per il disegno dei bounding box
    st.session_state['doc_dimensions'] = {
    'width': page.rect.width,
    'height': page.rect.height
    }
    
    #andiamo a richiamare il metodo pdfocr_tobytes per generare un PDF che incorpora i risultati OCR,
    #settando i vari parametri come compressione, lingua e percorso tessdata
    ocr_pdf_bytes = pix.pdfocr_tobytes(
    compress=True,
    language='eng+ita',
    tessdata= os.getenv("TESSDATA_PREFIX"),
    )
    
    #andiamo a memorizzare il PDF OCR nella session state
    #in modo tale da poterlo usare in seguito per il disegno dei bounding box ed infine chiudiamo il file
    st.session_state['ocr_pdf_bytes'] = ocr_pdf_bytes
    logging.info("OCR processing completed successfully")
    
    doc.close()