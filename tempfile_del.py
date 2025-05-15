import logging
import os
#andiamo a definire una funzione per eliminare il file temporaneo, in modo tale da non sovraccaricare il database
#e mantenere solo le più recenti, in caso di errore restituisce un log di errore
def delete_temp_file(file_path):
    #se il file non è definito, non facciamo nulla
    #altrimenti andiamo a dare il permesso di eliminare il file
    if not file_path:
        return
        
    try:
        #andiamo a definire il numero di tentativi per eliminare il file e per ogni tentativo
        #verifichiamo se il file esiste, in caso contrario non facciamo nulla
        attempts = 3
        for i in range(attempts):
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logging.info(f"Temporary file {file_path} deleted successfully.")
                    break
                except PermissionError as pe:
                    if i < attempts - 1:
                        logging.warning(f"File {file_path} is locked. Waiting before retry #{i+1}.")
                    else:
                        logging.warning(f"Could not delete {file_path} after {attempts} attempts: {pe}")
            else:
                #se il file non esiste, non facciamo nulla
                break
    except Exception as e:
        logging.error(f"Error deleting temporary file {file_path}: {e}")