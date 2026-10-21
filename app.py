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
# RENDER DIAGRAM RBD (2 BARIS)
# ============================================================
def draw_rbd(df):
    # Inisialisasi Graphviz
    dot = graphviz.Digraph(engine='dot')
    dot.attr(rankdir='LR', size='40,10', nodesep='0.5', ranksep='0.5')
    dot.attr('node', shape='box', style='filled', fontname='Arial', fontsize='10')
    
    def get_color(avail):
        if avail < 0.85: return '#FF6B6B' # Merah
        elif avail < 0.95: return '#FFD93D' # Kuning
        else: return '#6BCB77' # Hijau

    # --- START NODE ---
    dot.node('start', 'Start', shape='diamond', fillcolor='#90EE90')
    
    # --- BARIS 1 (ID 1 - 12) ---
    with dot.subgraph(name='cluster_row1') as c1:
        c1.attr(style='invis') # Sembunyikan border cluster
        prev = 'start'
        for _, row in df[df["ID"] <= 12].sort_values("ID").iterrows():
            node_id = f"n{row['ID']}"
            label = f"{row['ID']}. {row['Nama Sistem']}\nA: {row['Availability']*100:.2f}%"
            c1.node(node_id, label, fillcolor=get_color(row['Availability']))
            c1.edge(prev, node_id)
            prev = node_id

    # --- BARIS 2 (ID 13 - 23) ---
    # Kita urutkan dari ID 23 sampai 13 (dari kanan ke kiri)
    with dot.subgraph(name='cluster_row2') as c2:
        c2.attr(style='invis')
        # Titik sambung imajiner di kiri baris 2
        c2.node('row2_start', shape='point', width='0', style='invis')
        
        prev = 'row2_start'
        for _, row in df[df["ID"] > 12].sort_values("ID", ascending=False).iterrows():
            node_id = f"n{row['ID']}"
            label = f"{row['ID']}. {row['Nama Sistem']}\nA: {row['Availability']*100:.2f}%"
            c2.node(node_id, label, fillcolor=get_color(row['Availability']))
            c2.edge(prev, node_id)
            prev = node_id

    # --- STOP NODE ---
    dot.node('stop', 'Stop', shape='diamond', fillcolor='#FF6B6B')
    dot.edge(prev, 'stop')

    # --- KONEKSI ANTAR BARIS ---
    # Hubungkan ujung kanan baris 1 (ID 12) ke titik imajiner kiri baris 2
    dot.edge('n12', 'row2_start', style='invis') # invisible edge untuk memaksa posisi

    # Paksa Baris 1 dan Baris 2 berada di tingkat yang sama secara horizontal
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('start')
        s.node('n23') # Ujung kiri baris 2 sejajar dengan start

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
