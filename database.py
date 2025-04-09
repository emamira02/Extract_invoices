import sqlite3
import datetime
import json

#creiamo il nostro database SQLite e la tabella per memorizzare i dati estratti
def create_database():
    conn = sqlite3.connect('cronologia.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyze (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_file TEXT,
            data TEXT,
            dati_json TEXT
        )
    ''')
    conn.commit()
    conn.close()

#qua andiamo ad inserire i dati della cronologia affinchè vengano salvati ogni
#volta che l'utente esegue un'analyze
def add_analysis_history(conn, cursor, nome_file, dati_json):
    data = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO analyze (nome_file, data, dati_json) VALUES (?, ?, ?)", (nome_file, data, json.dumps(dati_json, ensure_ascii=False))) 
    conn.commit()

#usiamo questa funzione per recuperare i dati della cronologia, ordinati per data in ordine descendente
def get_crono(cursor):
    cursor.execute("SELECT * FROM analyze ORDER BY data DESC")
    return cursor.fetchall()

#qua invece andiamo a recuperare i dati di un'analyze specifica
#inserendo l'id dell'analyze, in modo da visualizzare i dati estratti e restituirli
#in formato JSON, per poi visualizzarli in un formato più leggibile
def get_data_analysis(cursor, id_analyse):
    cursor.execute("SELECT dati_json FROM analyze WHERE id = ?", (id_analyse,))
    risultato = cursor.fetchone()
    if risultato:
        return json.loads(risultato[0])
    return None

#usiamo questa funzione per eliminare le analyze più vecchie, in modo da non sovraccaricare il database
#e mantenere solo le più recenti
def delete_oldest_analysis(conn, cursor):
    """Deletes the oldest analysis entry from the analyze table."""
    cursor.execute("SELECT id FROM analyze ORDER BY data ASC LIMIT 1")
    oldest_entry = cursor.fetchone()
    if oldest_entry:
        oldest_id = oldest_entry[0]
        cursor.execute("DELETE FROM analyze WHERE id = ?", (oldest_id,))
        conn.commit()
        print(f"Deleted oldest analysis with ID: {oldest_id}") 
    else:
        print("No analysis entries found to delete.")