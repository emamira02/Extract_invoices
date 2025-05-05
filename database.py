import sqlite3
import datetime
import json
import logging

#andiamo a definire una funzione per connetterci
def get_db_connection():
    conn = sqlite3.connect('cronologia.db')
    return conn

#creiamo il nostro database SQLite e la tabella per memorizzare i dati estratti
def create_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analyze (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_file TEXT,
                data TEXT,
                dati_json TEXT,
                file_blob BLOB
            )
        ''')
        conn.commit()
        logging.info("Database table 'analyze' created or already exists.") 
    except sqlite3.Error as e:
        logging.error(f"Error creating table: {e}")
    finally:
        conn.close()

#qua andiamo a inserire i dati estratti nel database SQLite per memorizzare l'analisi nella 
#cronologia delle analisi effettuate ed evitare di doverla rifare ogni volta
def add_analysis_history(nome_file, dati_json, file_blob=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    data = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute("INSERT INTO analyze (nome_file, data, dati_json, file_blob) VALUES (?, ?, ?, ?)",
                      (nome_file, data, json.dumps(dati_json, ensure_ascii=False), file_blob))
        conn.commit()
        logging.info(f"Analysis history added for {nome_file}")
    except sqlite3.Error as e:
        logging.error(f"Error inserting data: {e}")
    finally:
        conn.close()

#usiamo questa funzione per recuperare i dati della cronologia, ordinati per data in ordine descendente
def get_crono():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, nome_file, data FROM analyze ORDER BY data DESC")
        result = cursor.fetchall()
        return result
    except sqlite3.Error as e:
        logging.error(f"Error fetching analysis history: {e}")
        return []
    finally:
        conn.close()

#qua invece andiamo a recuperare i dati di un'analyze specifica
#inserendo l'id dell'analyze, in modo da visualizzare i dati estratti e restituirli
#in formato JSON, per poi visualizzarli in un formato più leggibile
def get_data_analysis(id_analyse):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT dati_json, file_blob FROM analyze WHERE id = ?", (id_analyse,))
        risultato = cursor.fetchone()
        if risultato:
            data = json.loads(risultato[0])
            data["file_blob"] = risultato[1]
            return data
        return None
    except sqlite3.Error as e:
        logging.error(f"Error fetching data for analysis ID {id_analyse}: {e}")
        return None
    finally:
        conn.close()

#usiamo questa funzione per eliminare le analyze più vecchie, in modo da non sovraccaricare il database
#e mantenere solo le più recenti
def delete_oldest_analysis():
    """Deletes the oldest analysis entry from the analyze table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM analyze ORDER BY data ASC LIMIT 1")
        oldest_entry = cursor.fetchone()
        if oldest_entry:
            oldest_id = oldest_entry[0]
            cursor.execute("DELETE FROM analyze WHERE id = ?", (oldest_id,))
            conn.commit()
            logging.info(f"Deleted oldest analysis with ID: {oldest_id}")
        else:
            logging.info("No analysis entries found to delete.")
    except sqlite3.Error as e:
        logging.error(f"Error deleting oldest analysis: {e}")
    finally:
        conn.close()

#qua andiamo a definire la funzione per inserire i blob nel database SQLite
#inserendo il nome del file e il percorso del file blob
def insert_blob_data(nome_file, file_path):
    """Inserts a file as blob data into the analyze table."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        logging.info("Connected to SQLite")
        
        empphoto = convertToBinary_data(file_path)
        data = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT id FROM analyze WHERE nome_file = ? ORDER BY data DESC LIMIT 1", (nome_file,))
        result = cursor.fetchone()
        
        if result:
            cursor.execute("UPDATE analyze SET file_blob = ? WHERE id = ?", (empphoto, result[0]))
        else:
            sqlite_insert_blob_query = """INSERT INTO analyze (nome_file, data, file_blob) VALUES (?, ?, ?)"""
            data_tuple = (nome_file, data, empphoto)
            cursor.execute(sqlite_insert_blob_query, data_tuple)
            
        conn.commit()
        logging.info(f"File {nome_file} inserted successfully as blob data into SQLite table.")
    except sqlite3.Error as error:
        logging.error(f"Failed to insert blob data into SQLite table: {error}")
    finally:
        if conn:
            conn.close()
            logging.info("The SQLite connection is closed")

#qua andiamo a definire la funzione per convertire i file in formato binario
def convertToBinary_data(data):
    """Converts data to binary format."""
    with open(data, "rb") as file:
        blob_data = file.read()
    return blob_data