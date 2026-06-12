import pandas as pd
import streamlit as st
import urllib.parse

# --- CONFIGURAZIONE DELLA PAGINA (Deve essere la primissima istruzione) ---
st.set_page_config(page_title="Cineteca Crast", page_icon="🏆", layout="centered")

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

# --- LOGICA DEL CHATBOT STATISTICO ---
def risposta_chatbot(user_input, df):
    query = user_input.lower()
    
    if "film" in query and ("miglior" in query or "primo" in query or "vincitore" in query):
        classifica = df.groupby("Film")["Voto"].mean().reset_index()
        migliore = classifica.sort_values(by="Voto", ascending=False).iloc[0]
        return f"🎬 Il miglior film in assoluto è **{migliore['Film']}** con una media di **{migliore['Voto']:.2f} ⭐**."
    
    elif "film" in query and ("peggior" in query or "ultimo" in query):
        classifica = df.groupby("Film")["Voto"].mean().reset_index()
        peggiore = classifica.sort_values(by="Voto", ascending=True).iloc[0]
        return f"📉 Il film con la media più bassa è **{peggiore['Film']}** con **{peggiore['Voto']:.2f} ⭐**."
        
    elif "quanti" in query and "film" in query:
        tot_film = df["Film"].nunique()
        return f"🎥 Nella cineteca ci sono attualmente **{tot_film}** film unici votati."
    
    elif "chi" in query and ("voti" in query or "votato" in query) and "più" in query:
        stacanovista = df["Nome"].value_counts().idxmax()
        num_voti = df["Nome"].value_counts().max()
        return f"🍿 Il cinefilo più attivo è **{stacanovista}** con ben **{num_voti}** voti espressi!"
    
    elif "media" in query and "voti" in query:
        media_globale = df["Voto"].mean()
        return f"📊 La media matematica di tutti i voti dati nella cineteca è di **{media_globale:.2f} ⭐**."
    
    # Ricerca dinamica per persona
    for persona in df["Nome"].unique():
        if persona.lower() in query:
            df_p = df[df["Nome"] == persona]
            media_p = df_p["Voto"].mean()
            film_p = df_p["Film"].nunique()
            return f"👤 **{persona}** ha guardato e votato **{film_p}** film, mantenendo una media personale di **{media_p:.2f} ⭐**."

    # Ricerca dinamica per film
    for film in df["Film"].unique():
        if film.lower() in query:
            df_f = df[df["Film"] == film]
            media_f = df_f["Voto"].mean()
            voti_f = df_f["Voto"].count()
            return f"🔍 Il film **{film}** è stato votato da **{voti_f}** persone, raggiungendo una media di **{media_f:.2f} ⭐**."

    return "🤖 Scusami, non ho capito la domanda. Prova a chiedermi cose come:\n- *Chi ha votato più film?*\n- *Qual è il miglior film?*\n- *Quanti film ci sono?*\n- *Qual è la media di [Nome Persona] o i dati di [Titolo Film]?*"


# =====================================================================
# PAGINA 1: HOME & CHATBOT
# =====================================================================
def mostra_home():
    st.title("🏆 Benvenuto nella Cineteca Crast")
    st.markdown("""
    Questa è la dashboard ufficiale per gli amanti del cinema. Qui puoi tracciare i voti, 
    scoprire le tendenze del gruppo e sfidare le opinioni degli altri cinefili.
    
    👈 Usa la **barra laterale sinistra** per navigare tra le sezioni del sito!
    """)
    
    st.divider()
    st.subheader("🤖 Assistente Virtuale della Cineteca")
    st.caption("Chiedimi statistiche sui film, sulle persone o sulle medie globali!")

    if errore_dati:
        st.error("❌ Impossibile connettersi ai dati per alimentare il chatbot.")
        return

    # Inizializzazione della cronologia della chat
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Ciao! Sono il chatbot della Cineteca Crast. Chiedimi pure qualsiasi curiosità sulle classifiche!"}
        ]

    # Mostra i messaggi precedenti
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # Input dell'utente
    if user_query := st.chat_input("Inserisci la tua domanda (es. 'Qual è il miglior film?')"):
        st.chat_message("user").write(user_query)
        st.session_state.messages.append({"role": "user", "content": user_query})
        
        # Generazione risposta
        risposta = risposta_chatbot(user_query, df_data)
        
        st.chat_message("assistant").write(risposta)
        st.session_state.messages.append({"role": "assistant", "content": risposta})


# =====================================================================
# PAGINA 2: CLASSIFICHE 2026
# =====================================================================
def mostra_classifiche_2026():
    st.title("📊 Classifiche e Analisi - Anno 2026")
    
    if errore_dati:
        st.error("❌ Impossibile connettersi a Google Fogli o elaborare i dati.")
        return

    # --- CLASSIFICA GENERALE ---
    classifica = df_data.groupby("Film")["Voto"].mean().reset_index()
    classifica = classifica.rename(columns={"Film": "Films", "Voto": "Media"})
    
    if not classifica.empty:
        classifica_totale = classifica.sort_values(by="Media", ascending=False).reset_index(drop=True)
        classifica_totale.index = classifica_totale.index + 1
        classifica_totale = classifica_totale.reset_index().rename(columns={"index": "Posizione"})

        st.subheader("🥇 I Magnifici Tre")
        col1, col2, col3 = st.columns(3)
        if len(classifica_totale) >= 1:
            col1.metric("1° Posto 🥇", classifica_totale.iloc[0]['Films'], f"{classifica_totale.iloc[0]['Media']:.2f}")
        if len(classifica_totale) >= 2:
            col2.metric("2° Posto 🥈", classifica_totale.iloc[1]['Films'], f"{classifica_totale.iloc[1]['Media']:.2f}")
        if len(classifica_totale) >= 3:
            col3.metric("3° Posto 🥉", classifica_totale.iloc[2]['Films'], f"{classifica_totale.iloc[2]['Media']:.2f}")
        
        st.divider()

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
