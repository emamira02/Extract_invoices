# Usa un'immagine base Python ufficiale
FROM python:3.12-slim-bullseye

# Imposta la directory di lavoro all'interno del container
WORKDIR /app

# Copia il file requirements.txt e installa le dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia solo i file necessari
COPY frontend.py backend.py ./


# Imposta la porta su cui Streamlit verrà eseguito (la porta 8501 è quella predefinita)
EXPOSE 8501

# Comando per eseguire l'applicazione Streamlit
CMD ["streamlit", "run", "frontend.py"]