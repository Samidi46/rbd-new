import streamlit as st
import pandas as pd
import numpy as np
import graphviz
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="RBD PLTU Dashboard", layout="wide")
st.title("⚡ RBD Visual Dashboard — PLTU")
st.caption("Visualisasi Reliability Block Diagram. Warna merah = kritis, hijau = aman.")

# ============================================================
# KONEKSI GOOGLE SHEETS
# ============================================================
@st.cache_resource
def get_gsheet_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        key = creds_dict["private_key"]
        if "\\n" in key: key = key.replace("\\n", "\n")
        creds_dict["private_key"] = key
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_data():
    client = get_gsheet_client()
    sh = client.open_by_key(st.secrets["GSHEET_SPREADSHEET_ID"])
    
    # Baca sheet
    df_struktur = pd.DataFrame(sh.worksheet("Struktur_RBD").get_all_records())
    
    # Simulasi Data Availability per Group (karena fokus ke visual, kita pakai nilai dummy dulu)
    # Nanti bisa dihubungkan dengan perhitungan Weibull dari sheet Event_Log
    dummy_avail = {
        "FireProt": 0.99, "ProsesProt": 0.98, "ElecProt": 0.95, "EmergencyPower": 0.92,
        "ElecControl": 0.99, "CW": 0.75, # <--- CW sengaja dibuat rendah (merah) seperti di gambar
        "CCW": 0.90, "AirControl": 0.99, "CWT": 0.99, "FuelOil": 0.99,
        "AuxBoiler": 0.99, "Condensate": 0.99, "Feedwater": 0.85, "HeatGen": 0.98,
        "CoalHandling": 0.95, "Bunker": 0.98, "CombustionAir": 0.98, "BoilerFiring": 0.99,
        "AshSlag": 0.95, "Steam": 0.99, "Turbine": 0.70, # <--- Turbine sengaja dibuat rendah
        "Generator": 0.99, "Transmission": 0.99
    }
    
    # Gabungkan data struktur dengan data availability
    df_struktur["Availability"] = df_struktur["Equipment_Group"].map(dummy_avail).fillna(0.99)
    
    return df_struktur

# ============================================================
# RENDER DIAGRAM RBD (2 BARIS - RAPI & PASTI BERHASIL)
# ============================================================
def draw_rbd(df):
    # Gunakan engine 'dot' standar
    dot = graphviz.Digraph(engine='dot')
    
    # Atur jarak antar node
    dot.attr(rankdir='LR', ranksep='0.4', nodesep='0.4')
    dot.attr('node', shape='box', style='filled', fontname='Arial', fontsize='10', height='0.7', width='1.4')
    
    def get_color(avail):
        if avail < 0.85: return '#FF6B6B' # Merah
        elif avail < 0.95: return '#FFD93D' # Kuning
        else: return '#6BCB77' # Hijau

    # --- START NODE ---
    dot.node('start', 'Start', shape='diamond', fillcolor='#90EE90')

    # --- BARIS 1 (ID 1 - 12) ---
    prev = 'start'
    for _, row in df[df["ID"] <= 12].sort_values("ID").iterrows():
        node_id = f"n{row['ID']}"
        label = f"{row['ID']}. {row['Nama Sistem']}\nA: {row['Availability']*100:.2f}%"
        dot.node(node_id, label, fillcolor=get_color(row['Availability']))
        dot.edge(prev, node_id)
        prev = node_id

    # --- JEMBATAN TURUN (ID 12 ke ID 13) ---
    # Kita buat node bayangan agar garisnya turun lurus ke bawah
    dot.node('bridge', '', shape='point', width='0', style='invis')
    dot.edge('n12', 'bridge', style='invis') # Garis tak terlihat
    dot.edge('bridge', 'n13', style='invis') # Garis tak terlihat

    # --- BARIS 2 (ID 13 - 23) ---
    prev = 'bridge'
    for _, row in df[df["ID"] > 12].sort_values("ID").iterrows():
        node_id = f"n{row['ID']}"
        label = f"{row['ID']}. {row['Nama Sistem']}\nA: {row['Availability']*100:.2f}%"
        dot.node(node_id, label, fillcolor=get_color(row['Availability']))
        dot.edge(prev, node_id)
        prev = node_id

    # --- STOP NODE ---
    dot.node('stop', 'Stop', shape='diamond', fillcolor='#FF6B6B')
    dot.edge(prev, 'stop')

    # --- TRIK MUTLAK: Paksa Baris 2 Selalu di Bawah Baris 1 ---
    with dot.subgraph() as s1:
        s1.attr(rank='same')
        s1.node('start')
        s1.node('n1'); s1.node('n2'); s1.node('n3'); s1.node('n4'); s1.node('n5')
        s1.node('n6'); s1.node('n7'); s1.node('n8'); s1.node('n9'); s1.node('n10')
        s1.node('n11'); s1.node('n12')
        
    with dot.subgraph() as s2:
        s2.attr(rank='same')
        s2.node('n13'); s2.node('n14'); s2.node('n15'); s2.node('n16'); s2.node('n17')
        s2.node('n18'); s2.node('n19'); s2.node('n20'); s2.node('n21'); s2.node('n22')
        s2.node('n23'); s2.node('stop')

    return dot
    
# ============================================================
# MAIN APP
# ============================================================
try:
    df_struktur = load_data()
    
    st.markdown("### 🗺️ Peta Sistem PLTU")
    st.markdown("""
    *   🟩 **Hijau**: Availability > 95% (Aman)
    *   🟨 **Kuning**: Availability 85% - 95% (Waspada)
    *   🟥 **Merah**: Availability < 85% (Kritis)
    """)
    
    # Gambar diagram
    graph = draw_rbd(df_struktur)
    st.graphviz_chart(graph, use_container_width=True)
    
    # Tampilkan Tabel Pendukung
    st.markdown("### 📊 Data Detail Sistem")
    st.dataframe(df_struktur[["ID", "Nama Sistem", "Availability"]].style.format({"Availability": "{:.2%}"}), 
                 use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
    st.info("Pastikan Sheet 'Struktur_RBD' sudah dibuat dan nama-namanya sesuai.")
