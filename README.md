# Estrattore di Dati con Azure AI

Questo progetto fornisce un'applicazione Streamlit che estrae dati da fatture e ricevute utilizzando Azure AI Document Intelligence. Consente agli utenti di caricare documenti, analizzarli, modificare i dati estratti e scaricare i risultati in formato JSON. L'applicazione gestisce anche il login utente tramite Microsoft Azure Entra ID.

## Funzionalità

*   **Caricamento Documenti:** Supporta i formati di file PDF, JPG, JPEG e PNG.
*   **Estrazione con Azure AI:** Utilizza Azure AI Document Intelligence per estrarre informazioni rilevanti da fatture e ricevute.
*   **Modifica Dati:** Consente agli utenti di modificare i dati estratti in un'interfaccia intuitiva.
*   **Visualizzazione Dati:** Evidenzia i dati estratti sull'immagine del documento.
*   **Download JSON:** Fornisce un pulsante di download per i dati estratti e modificati in formato JSON.
*   **Autenticazione Utente:** Protegge l'accesso con il login di Microsoft Azure Entra ID tramite Streamlit's `st.experimental_user`.
*   **Dockerizzato:** Facilmente implementabile con Docker.

## Prerequisiti

*   **Azure Subscription:** Una sottoscrizione Azure attiva con accesso ad Azure AI Document Intelligence.
*   **Azure AI Document Intelligence Resource:** Una risorsa Document Intelligence creata nella tua sottoscrizione Azure. Avrai bisogno della chiave API e dell'endpoint per questa risorsa.
*   **Microsoft Azure Entra ID:** Un Microsoft Azure Entra ID per l'autenticazione utente. Devi registrare un'applicazione in Azure AD e ottenere il Client ID e il Client Secret.
*   **Python 3.12:** Python 3.12 o superiore installato.
*   **Docker:** Docker installato per la containerizzazione.

## Configurazione

1.  **Clona il repository:**

    ```bash
    git clone <URL_del_repository>
    cd <directory_del_repository>
    ```

2.  **Configura le Credenziali Azure AI:**

    *   Crea un file chiamato `client.ini` nella directory principale del progetto.
    *   Aggiungi il seguente contenuto a `client.ini`, sostituendo i segnaposto con la tua chiave API e URL endpoint effettivi:

        ```ini
        [DocumentAI]
        api_key = TUA_CHIAVE_API
        endpoint = TUO_URL_ENDPOINT
        ```

3.  **Configura l'Autenticazione con Microsoft Azure Entra ID:**

    *   **Registra un'applicazione in Azure Active Directory (Azure AD):** Segui la documentazione Microsoft per registrare un'applicazione in Azure AD. Otterrai un *Client ID* e dovrai generare un *Client Secret*. Imposta l'URL di reindirizzamento (Redirect URI) dell'applicazione a `http://localhost:8501` (o l'URL dove la tua applicazione Streamlit sarà accessibile).  Se l'app è in produzione, usa l'URL di produzione.

    *   **Configura `secrets.toml`:** Crea una directory `.streamlit` (se non esiste) nella directory principale del tuo progetto. All'interno di `.streamlit`, crea un file chiamato `secrets.toml`.

    *   **Aggiungi le credenziali Azure AD a `secrets.toml`:**  Questo file conterrà le credenziali per l'autenticazione.  **Non committare questo file in un repository pubblico!**

        ```toml
        [experimental.user]
        client_id = "YOUR_CLIENT_ID"  # Sostituisci con il Client ID della tua app Azure AD
        tenant_id = "YOUR_TENANT_ID"  #Sostituisci con il Tenant ID della tua app Azure AD
        cookie_secret = ""  #Inserisci una stringa qualsiasi
        client_secret = "YOUR_CLIENT_SECRET"  # Sostituisci con il Client Secret generato
        redirect_uri = "http://localhost:8501" #Sostituisci con il corretto redirect URI
        server_metadata_url = "YOUR_SERVER_URL"  #Sostituisci con il corretto URL del server metadata Microsoft   #Es.   https://login.microsoftonline.com/YOUR_TENANT_ID/v2.0/.well-known/openid-configuration
        allowed_emails = ["your_email@example.com", "another_email@example.com"] # opzionale: lista di email autorizzate
        ```

        *   Sostituisci `YOUR_CLIENT_ID`, `YOUR_TENANT_ID`, `YOUR_CLIENT_SECRET`, `YOUR_SERVER_URL`, `http://localhost:8501` con i valori corretti.
        *   La sezione `allowed_emails` è opzionale. Se presente, solo gli utenti con gli indirizzi email elencati potranno accedere all'applicazione.

4.  **Configura Tesseract OCR (Importante per una Migliore Qualità OCR):**

    *   Sebbene l'applicazione utilizzi l'OCR Tesseract integrato in PyMuPDF, puoi migliorare significativamente la precisione dell'OCR installando Tesseract sulla tua macchina host e fornendo il percorso alla sua directory tessdata.

    *   **Installa Tesseract:** Segui le istruzioni di installazione per il tuo sistema operativo. I metodi comuni includono:

        *   **Windows:** Scarica l'installer da [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) e installalo. Assicurati di aggiungere Tesseract alla variabile di ambiente PATH del tuo sistema durante l'installazione.
        *   **macOS:** `brew install tesseract` (se usi Homebrew)
        *   **Linux:** `sudo apt-get install tesseract-ocr` (Debian/Ubuntu) or `sudo yum install tesseract` (CentOS/RHEL)

    *   **Individua la directory `tessdata`:** Questa directory contiene i file di dati linguistici necessari per Tesseract. Il percorso tipico è:

        *   **Windows:** `C:\Program Files\Tesseract-OCR\tessdata`
        *   **macOS:** `/usr/local/share/tessdata` (se installato con Homebrew)
        *   **Linux:** `/usr/share/tesseract-ocr/tessdata`

    *   **Imposta la variabile d'ambiente `TESSDATA_PREFIX`:** Nel file `.env` (crealo se non esiste nella directory principale del progetto), aggiungi la seguente riga, sostituendo il percorso con quello corretto per il tuo sistema:

        ```
        TESSDATA_PREFIX = /usr/local/share/tessdata/
        ```

        Assicurati che il percorso sia corretto. Se non è impostato o è errato, l'OCR potrebbe non funzionare correttamente.

5.  **Installare le dipendenze Python:**

    ```bash
    pip install -r requirements.txt
    ```

6.  **Crea l'immagine Docker (nella directory principale del progetto):**

    ```bash
    docker build -t data-extractor .
    ```

7.  **Esegui il container Docker:**

    ```bash
    docker-compose up -d
    ```

## Utilizzo

1.  Apri il browser e vai all'indirizzo `http://localhost:8501`.
2.  Effettua il login con il tuo account Microsoft Azure Entra ID.
3.  Carica un file di fattura o ricevuta in formato PDF, JPG, JPEG o PNG.
4.  Attendi che l'applicazione analizzi il documento ed estragga i dati.
5.  Visualizza e modifica i dati estratti nell'interfaccia utente.
6.  Scarica i dati in formato JSON.

## Note

*   Per un corretto funzionamento del login di Microsoft, assicurati di aver configurato correttamente il file `.streamlit/secrets.toml` con il Client ID, Client Secret e Redirect URI corretti.
*   L'accuratezza dell'estrazione dei dati dipende dalla qualità del documento di input e dalle capacità del modello Azure AI Document Intelligence.
*   Se l'OCR non funziona correttamente, verifica che `TESSDATA_PREFIX` sia impostato correttamente e che i file di dati linguistici di Tesseract siano presenti nella directory specificata.
* Il modello prebuilt-receipt nel backend, viene utilizzato per estrapolare solo il MerchantPhoneNumber e il TransactionTime, qualora siano presenti nel documento, poichè il modello prebuilt-invoice non li estrae.

## Risoluzione dei problemi

*   **Errore di autenticazione:** Verifica che le impostazioni di Azure Active Directory siano configurate correttamente e che il file `secrets.toml` contenga il Client ID, Client Secret e Redirect URI corretti. Verifica anche che l'URL di reindirizzamento nell'applicazione Azure AD corrisponda a quello configurato in `secrets.toml`.
*   **Errore di estrazione dei dati:** Verifica che la chiave API e l'endpoint di Azure AI Document Intelligence siano corretti nel file `client.ini` e che la risorsa sia attiva nella tua sottoscrizione Azure.
*   **OCR non funzionante:** Verifica che la variabile d'ambiente `TESSDATA_PREFIX` sia impostata correttamente e che i file di dati linguistici di Tesseract siano presenti nella directory specificata.
*   **Errore di download:** Verifica i log dell'applicazione per identificare eventuali errori durante la creazione del link di download.