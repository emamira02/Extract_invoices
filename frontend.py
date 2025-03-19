import streamlit as st
import backend
import logging
from dotenv import load_dotenv

load_dotenv()

# settiamo come la pagina verrà visualizzata nei vari layout, espandendo lo schermo per visualizzare tutto
# centralmente e impostando il titolo della pagina
st.set_page_config(
    page_title= "Receipt Extractor",
    layout= "centered"
)

#andiamo a configurare la parte dei log
logging.basicConfig(
    filename= "app.log",  #commentare questa riga per inviare i log a stdout (per Docker)
    encoding="utf-8",
    filemode="a",       #questa riga aggiunge i vecchi log ai nuovi, append mode
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
    level=logging.INFO
)

#usando experimental_user andiamo a gestire il login dell'utente, se l'utente non è loggato mostra solo il pulsante di login
#altrimenti mostra il resto dell'app, inoltre andiamo a gestire il logout dell'utente, se un utente è loggato
#mostra il nome e l'email dell'utente
if not st.experimental_user.is_logged_in:
    st.title("Microsot Login:streamlit:")
    st.subheader(":material/Login: Please log in to continue")
    logging.info("Launched app, waiting for the User Login.")

    if st.button("Log in"):
        st.login()

else:
    if st.button("Log out"):
        st.logout()

    if st.experimental_user.is_logged_in:
        st.markdown(f"Hello, **{st.experimental_user.name}**, {st.experimental_user.email}")
        logging.info(f"User {st.experimental_user.name} ({st.experimental_user.email}) successfully logged in.")

#diamo un titolo alla nostra app, come presentazione usando qualche parametro per la grafica
    st.markdown("# Summarize a :red[PDF] with :red-background[one click]")

