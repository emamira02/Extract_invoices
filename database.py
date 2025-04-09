import sqlite3
import datetime
import json

#creiamo il nostro database SQLite e la tabella per memorizzare i dati estratti
def create_database():
    conn = sqlite3.connect('cronologia.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operazioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_file TEXT,
            data TEXT,
            dati_json TEXT
        )
    ''')
    conn.commit() 
    conn.close()

#qua andiamo ad inserire i dati della cronologia affinchè vengano salvati ogni
#volta che l'utente esegue un'analisi
def add_analisys_history(conn, cursor, nome_file, dati_json):
    data = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO operazioni (nome_file, data, dati_json) VALUES (?, ?, ?)", (nome_file, data, json.dumps(dati_json)))  # Salva i dati come JSON
    conn.commit()

#usiamo questa funzione per recuperare i dati della cronologia, ordinati per data in ordine descendente
def get_cronologia(cursor):
    cursor.execute("SELECT * FROM operazioni ORDER BY data DESC")
    return cursor.fetchall()

#qua invece andiamo a recuperare i dati di un'operazione specifica
#inserendo l'id dell'operazione, in modo da visualizzare i dati estratti e restituirli
#in formato JSON, per poi visualizzarli in un formato più leggibile
def get_dati_operazione(cursor, id_operazione):
    cursor.execute("SELECT dati_json FROM operazioni WHERE id = ?", (id_operazione,))
    risultato = cursor.fetchone()
    if risultato:
        return json.loads(risultato[0])
    return None
