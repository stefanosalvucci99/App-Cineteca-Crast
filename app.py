import pandas as pd
import streamlit as st

# Configurazione della pagina web
st.set_page_config(page_title="Cineteca Crast", page_icon="🏆", layout="centered")

st.title("🏆 Classifica Totale Cineteca Crast")
st.markdown("Benvenuto nella dashboard della tua cineteca! Ecco la classifica aggiornata in tempo reale.")

# --- CONFIGURAZIONE GOOGLE SHEETS ---
ID_FOGLIO = "19mu5-ZeEOR5AW7AfjmxalXOZioUODxQw3mYD6JKIRWY"

# Usiamo urllib.parse per gestire in modo sicuro gli spazi nel nome della scheda
import urllib.parse
NOME_SCHEDA = "Report Mensile"
NOME_SCHEDA_URL = urllib.parse.quote(NOME_SCHEDA)

# Costruiamo l'URL rimuovendo eventuali spazi di errore dall'ID
URL_FOGLIO_CSV = f"https://docs.google.com/spreadsheets/d/{ID_FOGLIO.strip()}/gviz/tq?tqx=out:csv&sheet={NOME_SCHEDA_URL}" 

try:
    # Caricamento del dataset direttamente da internet
    df = pd.read_csv(URL_FOGLIO_CSV, keep_default_na=False)
    
    # Pulizia dei nomi delle colonne (rimuove spazi bianchi)
    df.columns = df.columns.str.strip()
    
    # SE IL FOGLIO HA UNA COLONNA VUOTA ALL'INIZIO, PANDAS LA NOMINA "Unnamed: 0"
    # Sistemiamo i nomi se le colonne principali sono state lette male
    if "Films" not in df.columns and "B" in df.columns:
        # Tentativo di recupero se Pandas usa le lettere di Excel
        df = df.rename(columns={"B": "Films", "G": "Media"})

    if "Films" in df.columns and "Media" in df.columns:
        classifica = df[["Films", "Media"]].copy()

        # Pulizia dati: stringhe vuote o pulite
        classifica["Films"] = classifica["Films"].astype(str).str.strip()
        classifica = classifica[classifica["Films"] != ""]
        
        # Gestione dei numeri con la virgola italiana (es. 8,5 -> 8.5)
        classifica["Media"] = classifica["Media"].astype(str).str.replace(",", ".", regex=False)
        classifica["Media"] = pd.to_numeric(classifica["Media"], errors="coerce")
        
        # Rimuoviamo i valori nulli
        classifica = classifica.dropna(subset=["Media"])

        if not classifica.empty:
            # Ordinamento
            classifica_totale = classifica.sort_values(by="Media", ascending=False)
            classifica_totale = classifica_totale.reset_index(drop=True)
            classifica_totale.index = classifica_totale.index + 1
            
            # Prepariamo il dataframe per la visualizzazione web
            classifica_totale = classifica_totale.reset_index().rename(columns={"index": "Posizione"})

            # --- Podio Visivo ---
            st.subheader("🥇 I Magnifici Tre")
            col1, col2, col3 = st.columns(3)
            
            if len(classifica_totale) >= 1:
                col1.metric("1° Posto 🥇", classifica_totale.iloc[0]['Films'], f"{classifica_totale.iloc[0]['Media']:.2f}")
            if len(classifica_totale) >= 2:
                col2.metric("2° Posto 🥈", classifica_totale.iloc[1]['Films'], f"{classifica_totale.iloc[1]['Media']:.2f}")
            if len(classifica_totale) >= 3:
                col3.metric("3° Posto 🥉", classifica_totale.iloc[2]['Films'], f"{classifica_totale.iloc[2]['Media']:.2f}")
            
            st.divider()

            # --- Tabella Completa Interattiva ---
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
            st.warning("⚠️ Nessun film convertito correttamente. Controlla che i voti nella colonna Media siano numeri validi.")
    else:
        st.error("❌ Errore di intestazione.")
        st.info(f"Colonne rilevate: {list(df.columns)}")

except Exception as e:
    st.error(f"❌ Impossibile connettersi a Google Fogli. Verifica il link o la connessione internet.")
    st.caption(f"Dettaglio errore: {e}")

# Bottone per forzare l'aggiornamento dei dati
st.button("🔄 Aggiorna Dati")