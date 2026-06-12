import pandas as pd
import streamlit as st
import urllib.parse
from openai import OpenAI  # <--- Nuova libreria per l'AI

# --- CONFIGURAZIONE DELLA PAGINA (Deve essere la primissima istruzione) ---
st.set_page_config(page_title="Cineteca Crast", page_icon="🏆", layout="centered")

# --- INIZIALIZZAZIONE CLIENT OPENAI ---
# Streamlit leggerà automaticamente la chiave da .streamlit/secrets.toml
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    client = None

# --- CONFIGURAZIONE GOOGLE SHEETS ---
ID_FOGLIO = "1ewvtkUtp31Qeo-mpjXafuTQsyZEgiC06eS-EGCwao_8"
NOME_SCHEDA_PIATTA = "Tabella Piatta"

NOME_SCHEDA_PIATTA_URL = urllib.parse.quote(NOME_SCHEDA_PIATTA)
URL_TABELLA_PIATTA = f"https://docs.google.com/spreadsheets/d/{ID_FOGLIO.strip()}/gviz/tq?tqx=out:csv&sheet={NOME_SCHEDA_PIATTA_URL}"

# Funzione di caching per evitare di ricaricare il foglio a ogni interazione del chatbot
@st.cache_data(ttl=600)
def carica_dati():
    df_piatto = pd.read_csv(URL_TABELLA_PIATTA, keep_default_na=False)
    df_piatto.columns = df_piatto.columns.str.strip()
    
    # Conversione e pulizia
    df_piatto["Voto"] = df_piatto["Voto"].astype(str).str.replace(",", ".", regex=False)
    df_piatto["Voto"] = pd.to_numeric(df_piatto["Voto"], errors="coerce")
    df_piatto = df_piatto.dropna(subset=["Voto"])
    df_piatto["Film"] = df_piatto["Film"].astype(str).str.strip()
    df_piatto["Nome"] = df_piatto["Nome"].astype(str).str.strip()
    df_piatto = df_piatto[df_piatto["Film"] != ""]
    return df_piatto

# Caricamento dati centralizzato con gestione errori
try:
    df_data = carica_dati()
    errore_dati = False
except Exception as e:
    errore_dati = True

# --- NUOVA LOGICA DEL CHATBOT CON VERA AI ---
def risposta_chatbot_ai(user_input, df, messaggi_precedenti):
    if client is None:
        return "⚠️ Errore: Chiave API di OpenAI non configurata nei Secrets di Streamlit."

    # 1. Prepariamo un riassunto dei dati da dare in pasto all'AI come contesto
    classifica = df.groupby("Film")["Voto"].agg(["mean", "count"]).reset_index()
    classifica_str = classifica.to_string(index=False)
    
    utenti = df.groupby("Nome")["Voto"].agg(["mean", "count"]).reset_index()
    utenti_str = utenti.to_string(index=False)

    # 2. Definiamo le istruzioni di sistema (raddoppiate le graffe per i titoli di sezione)
    system_prompt = f"""
    Sei l'assistente virtuale ufficiale della 'Cineteca Crast', un gruppo di cinefili che vota i film.
    Il tuo compito è rispondere alle domande degli utenti basandoti RIGOROSAMENTE sui dati reali del database che ti forniamo qui sotto.
    
    Ecco i dati attuali della Cineteca:
    
    --- CLASSIFICA FILM (Media voti e numero di persone che lo hanno votato) ---
    {classifica_str}
    
    --- STATISTICHE UTENTI (Media personale e numero di film votati) ---
    {utenti_str}
    
    Regole di comportamento:
    1. Sii simpatico, ironico e appassionato di cinema, ma preciso con i numeri.
    2. Usa le emoji relative al cinema (🎬, 🍿, ⭐, 📊).
    3. Se l'utente ti chiede pareri generali su film non presenti nel database, puoi rispondere come un esperto di cinema, ma specifica che quel film non è ancora stato votato nella Cineteca Crast.
    4. Rispondi in italiano.
    """

    # 3. Costruiamo lo storico della conversazione da inviare alle API
    messages = [{"role": "system", "content": system_prompt}]
    
    # Includiamo gli ultimi
