# Usa un'immagine base Python ufficiale
FROM python:3.12-bullseye

# Imposta la directory di lavoro all'interno del container
WORKDIR /app

# Copia il file requirements.txt e installa le dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt update && apt install -y autoconf automake libtool pkg-config libpng-dev libtiff5-dev zlib1g-dev libwebpdemux2 libwebp-dev libopenjp2-7-dev libgif-dev libarchive-dev libcurl4-openssl-dev libicu-dev libpango1.0-dev libcairo2-dev libleptonica-dev

RUN git clone https://github.com/tesseract-ocr/tesseract.git && cd tesseract && ./autogen.sh && ./configure --with-extra-includes=/usr/include --with-extra-libs=/usr/lib/x86_64-linux-gnu/ --prefix=/usr/local && make -j4 && make install && ldconfig

ADD resources /usr/local/share/tessdata

# Copia solo i file necessari
COPY frontend.py backend.py database.py ./
COPY pages ./pages

ENV TESSDATA_PREFIX=/usr/local/share/tessdata/

# Imposta la porta su cui Streamlit verrà eseguito (la porta 8501 è quella predefinita)
EXPOSE 8501

# Comando per eseguire l'applicazione Streamlit
CMD ["streamlit", "run", "frontend.py"]