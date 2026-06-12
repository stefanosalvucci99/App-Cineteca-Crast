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
    # Generiamo classifiche e statistiche generali pronte per essere lette dall'AI
    classifica = df.groupby("Film")["Voto"].agg(["mean", "count"]).reset_index()
    classifica_str = classifica.to_string(index=False)
    
    utenti = df.groupby("Nome")["Voto"].agg(["mean", "count"]).reset_index()
    utenti_str = utenti.to_string(index=False)

    # 2. Definiamo le istruzioni di sistema (il "carattere" e le conoscenze dell'AI)
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
    
    # Includiamo gli ultimi messaggi per mantenere la memoria della chat (evitiamo di mandare millenni di cronologia)
    for msg in messaggi_precedenti[-6:]: 
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    # Aggiungiamo l'ultima domanda dell'utente
    messages.append({"role": "user", "content": user_input})

    try:
        # 4. Chiamata API (usiamo gpt-4o-mini che è velocissimo ed economico)
        risposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        return risposta.choices[0].message.content
    except Exception as e:
        return f"❌ Errore durante la generazione della risposta: {str(e)}"


# =====================================================================
# PAGINA 1: HOME & CHATBOT
# =====================================================================
def mostra_home():
    st.title("🏆 Benvenuto nella Cineteca Crast")
    st.markdown("""
    Questa è la dashboard ufficiale per gli amanti del cinema. Qui puoi tracciare i voti, 
    scoprire le trends del gruppo e sfidare le opinioni degli altri cinefili.
    
    👈 Usa la **barra laterale sinistra** per navigare tra le sezioni del sito!
    """)
    
    st.divider()
    st.subheader("🤖 Assistente Virtuale della Cineteca")
    st.caption("Chiedimi statistiche sui film, consigli o analisi sui voti dei cinefili!")

    if errore_dati:
        st.error("❌ Impossibile connettersi ai dati per alimentare il chatbot.")
        return

    # Inizializzazione della cronologia della chat
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Ciao! Sono l'AI della Cineteca Crast. Chiedimi pure qualsiasi curiosità sulle classifiche, medie o opinioni del gruppo!"}
        ]

    # Mostra i messaggi precedenti
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # Input dell'utente
    if user_query := st.chat_input("Inserisci la tua domanda (es. 'Chi ha la media voti più alta?')"):
        st.chat_message("user").write(user_query)
        
        # Generazione risposta tramite AI (passando la cronologia per la memoria)
        with st.spinner("L'AI sta analizzando i dati..."):
            risposta = risposta_chatbot_ai(user_query, df_data, st.session_state.messages)
        
        st.chat_message("assistant").write(risposta)
        
        # Salviamo nello stato sia l'input utente che la risposta AI
        st.session_state.messages.append({"role": "user", "content": user_query})
        st.session_state.messages.append({"role": "assistant", "content": risposta})


# =====================================================================
# PAGINA 2: CLASSIFICHE 2026 (Modificata con "I peggiori 5 💩")
# =====================================================================
def mostra_classifiche_2026():
    st.title("📊 Classifiche e Analisi - Anno 2026")
    
    if errore_dati:
        st.error("❌ Impossibile connettersi a Google Fogli o elaborare i dati.")
        return

    # --- ELABORAZIONE CLASSIFICA GENERALE ---
    classifica = df_data.groupby("Film")["Voto"].mean().reset_index()
    classifica = classifica.rename(columns={"Film": "Films", "Voto": "Media"})
    
    if not classifica.empty:
        # Generazione classifica dei migliori (Decrescente)
        classifica_totale = classifica.sort_values(by="Media", ascending=False).reset_index(drop=True)
        classifica_totale.index = classifica_totale.index + 1
        classifica_totale = classifica_totale.reset_index().rename(columns={"index": "Posizione"})

        # --- SEZIONE: I MIGLIORI TRE ---
        st.subheader("🥇 I Magnifici Tre")
        col1, col2, col3 = st.columns(3)
        if len(classifica_totale) >= 1:
            col1.metric("1° Posto 🥇", classifica_totale.iloc[0]['Films'], f"{classifica_totale.iloc[0]['Media']:.2f}")
        if len(classifica_totale) >= 2:
            col2.metric("2° Posto 🥈", classifica_totale.iloc[1]['Films'], f"{classifica_totale.iloc[1]['Media']:.2f}")
        if len(classifica_totale) >= 3:
            col3.metric("3° Posto 🥉", classifica_totale.iloc[2]['Films'], f"{classifica_totale.iloc[2]['Media']:.2f}")
        
        st.divider()

        # --- NUOVA SEZIONE: I PEGGIORI 5 ---
        st.subheader("💩 I Peggiori 5 del 2026")
        st.caption("I film che hanno ottenuto la media voto più bassa all'interno della Cineteca.")
        
        # Ordiniamo in senso crescente per prendere i voti più bassi
        peggiori_5 = classifica.sort_values(by="Media", ascending=True).head(5).reset_index(drop=True)
        peggiori_5.index = peggiori_5.index + 1
        peggiori_5 = peggiori_5.reset_index().rename(columns={"index": "Flop"})
        
        st.dataframe(
            peggiori_5,
            column_config={
                "Flop": st.column_config.NumberColumn("Pos.", format="%d"),
                "Films": st.column_config.TextColumn("Titolo del Film da Evitare"),
                "Media": st.column_config.NumberColumn("Media Voti", format="%.2f 💩")
            },
            hide_index=True,
            use_container_width=True
        )

        st.divider()

        # --- SEZIONE: CLASSIFICA COMPLETA ---
        st.subheader("📋 Classifica Completa")
        st.dataframe(
            classifica_totale, 
            column_config={
                "Posizione": st.column_config.NumberColumn("Pos.", format="%d"),
                "Films": st.column_config.TextColumn("Titolo del Film"),
                "Media": st.column_config.NumberColumn("Media Voti", format="%.2f ⭐")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning("⚠️ Nessun film presente nel database.")

    st.divider()

    # --- ANALISI PERSONALE ---
    st.subheader("📈 Analisi Voti Personali e Differenziali")
    
    lista_persone = sorted(df_data["Nome"].unique())
    persona_scelta = st.selectbox("Seleziona una persona per vedere le sue statistiche:", lista_persone)
    
    if persona_scelta:
        df_persona = df_data[df_data["Nome"] == persona_scelta].copy()
        statistiche_film = df_data.groupby("Film")["Voto"].agg(["sum", "count"]).reset_index()
        df_analisi = pd.merge(df_persona, statistiche_film, on="Film", how="left")
        
        df_analisi["Media_Altri"] = (df_analisi["sum"] - df_analisi["Voto"]) / (df_analisi["count"] - 1)
        df_analisi["Media_Altri"] = df_analisi["Media_Altri"].fillna(df_analisi["Voto"])
        df_analisi["Differenziale"] = df_analisi["Voto"] - df_analisi["Media_Altri"]
        df_analisi = df_analisi.sort_values(by="Voto", ascending=False)
        
        st.write(f"### 📊 Tutti i voti di {persona_scelta}")
        st.bar_chart(data=df_analisi, x="Film", y="Voto", color="#FF4B4B", use_container_width=True)
        
        st.write(f"### ⚖️ Differenziale Voti (Rispetto alla media degli altri)")
        st.caption("Un valore positivo indica che hai dato un voto più alto rispetto alla media degli altri; un valore negativo indica il contrario.")
        st.bar_chart(data=df_analisi, x="Film", y="Differenziale", color="#29B5E8", use_container_width=True)
        
        with st.expander("🔍 Vedi i dati dettagliati del differenziale"):
            df_tabella = df_analisi[["Film", "Voto", "Media_Altri", "Differenziale"]].copy()
            df_tabella = df_tabella.rename(columns={
                "Voto": f"Voto di {persona_scelta}",
                "Media_Altri": "Media degli altri",
                "Differenziale": "Differenziale (Tu vs Altri)"
            })
            st.dataframe(df_tabella, hide_index=True, use_container_width=True)


# =====================================================================
# CONFIGURAZIONE NAVIGAZIONE VERTICALE (Sidebar)
# =====================================================================
azione_selezionata = st.navigation([
    st.Page(mostra_home, title="Home", icon="🏠"),
    st.Page(mostra_classifiche_2026, title="Classifiche 2026", icon="📅")
])

# Rendering della pagina attiva
azione_selezionata.run()

# --- FOOTER COMUNE A ENTRAMBE LE PAGINE con tasto reset cache ---
st.sidebar.divider()
if st.sidebar.button("🔄 Aggiorna Dati Fogli Google", use_container_width=True):
    st.cache_data.clear()
    st.sidebar.success("Dati aggiornati!")
    st.rerun()
