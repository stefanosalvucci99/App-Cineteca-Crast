import pandas as pd
import streamlit as st
import urllib.parse

# Configurazione della pagina web
st.set_page_config(page_title="Cineteca Crast", page_icon="🏆", layout="centered")

st.title("🏆 Classifica Totale Cineteca Crast")
st.markdown("Benvenuto nella dashboard della tua cineteca! Ecco la classifica aggiornata in tempo reale.")

# --- CONFIGURAZIONE GOOGLE SHEETS ---
ID_FOGLIO = "19mu5-ZeEOR5AW7AfjmxalXOZioUODxQw3mYD6JKIRWY"
NOME_SCHEDA_PIATTA = "Tabella Piatta"
NOME_SCHEDA_PIATTA_URL = urllib.parse.quote(NOME_SCHEDA_PIATTA)
URL_TABELLA_PIATTA = f"https://docs.google.com/spreadsheets/d/{ID_FOGLIO.strip()}/gviz/tq?tqx=out:csv&sheet={NOME_SCHEDA_PIATTA_URL}"

try:
    # 1. SCARICAMENTO E PULIZIA DATI (singola chiamata al foglio "Tabella Piatta")
    df_piatto = pd.read_csv(URL_TABELLA_PIATTA, keep_default_na=False)
    df_piatto.columns = df_piatto.columns.str.strip()
    
    # Conversione e pulizia dei dati fondamentali
    df_piatto["Voto"] = df_piatto["Voto"].astype(str).str.replace(",", ".", regex=False)
    df_piatto["Voto"] = pd.to_numeric(df_piatto["Voto"], errors="coerce")
    df_piatto = df_piatto.dropna(subset=["Voto"])
    df_piatto["Film"] = df_piatto["Film"].astype(str).str.strip()
    df_piatto["Nome"] = df_piatto["Nome"].astype(str).str.strip()
    df_piatto = df_piatto[df_piatto["Film"] != ""]

    # =====================================================================
    # BLOCCO 1: CLASSIFICA GENERALE (Calcolata da "Tabella Piatta")
    # =====================================================================
    # Calcoliamo la media globale per ogni film direttamente dai voti singoli
    classifica = df_piatto.groupby("Film")["Voto"].mean().reset_index()
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

        st.subheader("📊 Classifica Completa")
        st.dataframe(
            classifica_totale, 
            column_config={
                "Posizione": st.column_config.NumberColumn("Pos.", format="%d"),
                "Films": st.column_config.TextColumn("Titolo del Film"),
                "Media": st.column_config.NumberColumn("Media Voti", format="%.2f ⭐")
            },
            hide_index=True,
            width="stretch"
        )
    else:
        st.warning("⚠️ Nessun film presente nel database.")

    st.divider()

    # =====================================================================
    # BLOCCO 2: ANALISI PERSONALE (Sempre da "Tabella Piatta")
    # =====================================================================
    st.subheader("📈 Analisi Voti Personali e Differenziali")
    
    lista_persone = sorted(df_piatto["Nome"].unique())
    persona_scelta = st.selectbox("Seleziona una persona per vedere le sue statistiche:", lista_persone)
    
    if persona_scelta:
        df_persona = df_piatto[df_piatto["Nome"] == persona_scelta].copy()
        
        # Calcoliamo la somma e il conteggio dei voti totali per l'algoritmo del differenziale
        statistiche_film = df_piatto.groupby("Film")["Voto"].agg(["sum", "count"]).reset_index()
        
        df_analisi = pd.merge(df_persona, statistiche_film, on="Film", how="left")
        
        # Calcolo della media degli ALTRI partecipanti
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

except Exception as e:
    st.error("❌ Impossibile connettersi a Google Fogli o elaborare i dati.")

st.divider()

# Bottone per forzare l'aggiornamento dei dati svuotando la cache
if st.button("🔄 Aggiorna Dati"):
    st.cache_data.clear()
    st.rerun()
