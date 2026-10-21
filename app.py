import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="RBD PLTU Dashboard", layout="wide")
st.title("⚡ RBD Visual Dashboard — PLTU")
st.caption("Visualisasi Reliability Block Diagram. Data live dari Google Sheets.")

# ============================================================
# KONEKSI GOOGLE SHEETS
# ============================================================
@st.cache_resource
def get_gsheet_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            key = creds_dict["private_key"]
            if "\\n" in key: key = key.replace("\\n", "\n")
            if "-----BEGIN PRIVATE KEY-----" not in key:
                key = f"-----BEGIN PRIVATE KEY-----\n{key}\n-----END PRIVATE KEY-----\n"
            creds_dict["private_key"] = key
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly",
                  "https://www.googleapis.com/auth/drive.readonly"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Gagal koneksi ke Google: {e}")
        st.stop()

@st.cache_data(ttl=60)
def load_data(spreadsheet_id: str):
    client = get_gsheet_client()
    sh = client.open_by_key(spreadsheet_id)
    df_struktur = pd.DataFrame(sh.worksheet("Struktur_RBD").get_all_records())
    
    # --- SIMULASI DATA (Agar Anda bisa melihat variasi warna RI) ---
    # Format: "Equipment_Group": {"RI": Nilai Reliability Index, "A": Nilai Availability}
    dummy_data = {
        "FireProt": {"RI": 0.99, "A": 0.99}, 
        "ProsesProt": {"RI": 0.85, "A": 0.98}, 
        "ElecProt": {"RI": 0.75, "A": 0.95}, 
        "EmergencyPower": {"RI": 0.55, "A": 0.92},
        "ElecControl": {"RI": 0.90, "A": 0.99}, 
        "CW": {"RI": 0.15, "A": 0.75}, # Very Poor (Hitam)
        "CCW": {"RI": 0.35, "A": 0.90}, # Poor (Merah)
        "AirControl": {"RI": 0.95, "A": 0.99}, 
        "CWT": {"RI": 0.99, "A": 0.99}, 
        "FuelOil": {"RI": 0.85, "A": 0.99},
        "AuxBoiler": {"RI": 0.70, "A": 0.99}, 
        "Condensate": {"RI": 0.99, "A": 0.99}, 
        "Feedwater": {"RI": 0.45, "A": 0.85}, # Quite (Kuning)
        "HeatGen": {"RI": 0.88, "A": 0.98},
        "CoalHandling": {"RI": 0.65, "A": 0.95}, 
        "Bunker": {"RI": 0.92, "A": 0.98}, 
        "CombustionAir": {"RI": 0.85, "A": 0.98}, 
        "BoilerFiring": {"RI": 0.95, "A": 0.99},
        "AshSlag": {"RI": 0.70, "A": 0.95}, 
        "Steam": {"RI": 0.99, "A": 0.99}, 
        "Turbine": {"RI": 0.25, "A": 0.70}, # Poor (Merah)
        "Generator": {"RI": 0.85, "A": 0.99}, 
        "Transmission": {"RI": 0.99, "A": 0.99}
    }
    
    # Map data simulasi ke dataframe
    df_struktur["RI"] = df_struktur["Equipment_Group"].map(lambda x: dummy_data.get(x, {"RI": 0.99})["RI"])
    df_struktur["Availability"] = df_struktur["Equipment_Group"].map(lambda x: dummy_data.get(x, {"A": 0.99})["A"])
    
    return df_struktur

# ============================================================
# RENDER DIAGRAM RBD (HTML & CSS) - DENGAN RELIABILITY INDEX
# ============================================================
def draw_rbd_html(df):
    def get_color(ri):
        # Kriteria berdasarkan gambar referensi Anda
        if ri >= 0.81: return '#4b8c36' # Hijau Gelap (Very Good)
        elif ri >= 0.61: return '#92d050' # Hijau Muda (Good)
        elif ri >= 0.41: return '#ffff00' # Kuning (Quite)
        elif ri >= 0.21: return '#ff0000' # Merah (Poor)
        else: return '#000000' # Hitam (Very Poor)
    
    def get_text_color(ri):
        # Teks hitam untuk kuning & hijau muda. Teks putih untuk sisanya.
        if 0.41 <= ri < 0.81: return 'black'
        else: return 'white'

    def create_box(row):
        ri = row['RI']
        avail = row['Availability']
        color = get_color(ri)
        text_color = get_text_color(ri)
        
        return f"""
        <div style="
            background-color: {color};
            color: {text_color};
            border: 1px solid #333;
            border-radius: 5px;
            padding: 6px;
            width: 140px;
            height: 70px;
            text-align: center;
            font-family: Arial, sans-serif;
            font-size: 11px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
            margin: 0 4px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        ">
            <strong style="font-size: 11px; margin-bottom: 2px;">{row['ID']}. {row['Nama Sistem']}</strong>
            <span style="font-weight: bold; font-size: 12px;">R: {ri*100:.1f}%</span>
            <span style="font-size: 10px;">A: {avail*100:.1f}%</span>
        </div>
        """

    # Pisahkan baris
    row1 = df[df["ID"] <= 12].sort_values("ID")
    row2 = df[df["ID"] > 12].sort_values("ID", ascending=False) 

    # Susun HTML
    html_content = f"""
    <div style="display: flex; flex-direction: column; align-items: center; overflow-x: auto; padding: 20px; background-color: #f9f9f9; border-radius: 10px;">
        
        <!-- BARIS 1: START + ID 1-12 -->
        <div style="display: flex; flex-direction: row; flex-wrap: nowrap; align-items: center; margin-bottom: 30px;">
            <div style="background-color: #90EE90; padding: 10px 15px; border: 1px solid #333; border-radius: 5px; font-weight: bold; margin-right: 10px; height: 40px; display: flex; align-items: center;">
                START
            </div>
            <div style="font-size: 18px; color: #555; margin-right: 5px;">➡️</div>
    """
    
    for _, row in row1.iterrows():
        html_content += create_box(row)
        html_content += "<div style='font-size: 18px; color: #555; margin: 0 2px;'>➡️</div>"
    
    # Potong panah terakhir di baris 1
    html_content = html_content.rsplit("<div style='font-size: 18px; color: #555; margin: 0 2px;'>➡️</div>", 1)[0]

    html_content += """
        </div>
        
        <!-- BARIS 2: STOP + ID 23-13 -->
        <div style="display: flex; flex-direction: row; flex-wrap: nowrap; align-items: center;">
    """
    
    # STOP NODE di paling kiri Baris 2
    html_content += """
            <div style="background-color: #FF6B6B; color: white; padding: 10px 15px; border: 1px solid #333; border-radius: 5px; font-weight: bold; margin-right: 10px; height: 40px; display: flex; align-items: center;">
                STOP
            </div>
            <div style="font-size: 18px; color: #555; margin-right: 5px;">⬅️</div>
    """
    
    for _, row in row2.iterrows():
        html_content += create_box(row)
        html_content += "<div style='font-size: 18px; color: #555; margin: 0 2px;'>⬅️</div>"
        
    # Potong panah terakhir di baris 2
    html_content = html_content.rsplit("<div style='font-size: 18px; color: #555; margin: 0 2px;'>⬅️</div>", 1)[0]

    html_content += """
        </div>
    </div>
    """
    return html_content

# ============================================================
# MAIN APP
# ============================================================
try:
    spreadsheet_id = st.secrets["GSHEET_SPREADSHEET_ID"]
    df_struktur = load_data(spreadsheet_id)
    
    st.markdown("### 🗺️ Peta Sistem PLTU")
    
    # Tampilkan Legenda Warna
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.markdown("🟩 **> 0.80** (Very Good)")
    col2.markdown("🟩 **0.61 - 0.80** (Good)")
    col3.markdown("🟨 **0.41 - 0.60** (Quite)")
    col4.markdown("🟥 **0.21 - 0.40** (Poor)")
    col5.markdown("⬛ **0.00 - 0.20** (Very Poor)")
    
    st.write("") # Spasi
    
    # Render Diagram HTML
    html_diagram = draw_rbd_html(df_struktur)
    components.html(html_diagram, height=250, scrolling=True)
    
    # Tampilkan Tabel Pendukung (Update dengan RI)
    st.markdown("### 📊 Data Detail Sistem")
    df_show = df_struktur[["ID", "Nama Sistem", "RI", "Availability"]].copy()
    df_show["RI"] = df_show["RI"] * 100
    df_show["Availability"] = df_show["Availability"] * 100
    
    st.dataframe(df_show.style.format({"RI": "{:.1f}%", "Availability": "{:.1f}%"}), 
                 use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
    st.info("Pastikan Sheet 'Struktur_RBD' sudah dibuat dan nama-namanya sesuai.")
