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
    
    # Simulasi Data Availability 
    dummy_avail = {
        "FireProt": 0.99, "ProsesProt": 0.98, "ElecProt": 0.95, "EmergencyPower": 0.92,
        "ElecControl": 0.99, "CW": 0.75, 
        "CCW": 0.90, "AirControl": 0.99, "CWT": 0.99, "FuelOil": 0.99,
        "AuxBoiler": 0.99, "Condensate": 0.99, "Feedwater": 0.85, "HeatGen": 0.98,
        "CoalHandling": 0.95, "Bunker": 0.98, "CombustionAir": 0.98, "BoilerFiring": 0.99,
        "AshSlag": 0.95, "Steam": 0.99, "Turbine": 0.70, 
        "Generator": 0.99, "Transmission": 0.99
    }
    
    df_struktur["Availability"] = df_struktur["Equipment_Group"].map(dummy_avail).fillna(0.99)
    return df_struktur

# ============================================================
# RENDER DIAGRAM RBD (HTML & CSS)
# ============================================================
def draw_rbd_html(df):
    def get_color(avail):
        if avail < 0.85: return '#FF6B6B' # Merah
        elif avail < 0.95: return '#FFD93D' # Kuning
        else: return '#6BCB77' # Hijau
    
    def get_text_color(avail):
        return 'black' if 0.85 <= avail < 0.95 else 'white'

    def create_box(row):
        color = get_color(row['Availability'])
        text_color = get_text_color(row['Availability'])
        return f"""
        <div style="
            background-color: {color};
            color: {text_color};
            border: 1px solid #333;
            border-radius: 5px;
            padding: 6px;
            width: 130px;
            height: 60px;
            text-align: center;
            font-family: Arial, sans-serif;
            font-size: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
            margin: 0 4px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        ">
            <strong style="font-size: 11px;">{row['ID']}. {row['Nama Sistem']}</strong>
            <span>A: {row['Availability']*100:.2f}%</span>
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
            <!-- START NODE -->
            <div style="background-color: #90EE90; padding: 10px 20px; border: 1px solid #333; border-radius: 5px; font-weight: bold; margin-right: 10px; height: 40px; display: flex; align-items: center;">
                START
            </div>
            <div style="font-size: 20px; color: #555; margin-right: 10px;">➡️</div>
    """
    
    for _, row in row1.iterrows():
        html_content += create_box(row)
        html_content += "<div style='font-size: 20px; color: #555; margin: 0 4px;'>➡️</div>"
    
    # Potong panah terakhir di baris 1
    html_content = html_content.rsplit("<div style='font-size: 20px; color: #555; margin: 0 4px;'>➡️</div>", 1)[0]

    html_content += """
        </div>
        
        <!-- BARIS 2: STOP + ID 23-13 -->
        <div style="display: flex; flex-direction: row; flex-wrap: nowrap; align-items: center;">
    """
    
    # STOP NODE (diletakkan di paling kiri Baris 2)
    html_content += """
            <div style="background-color: #FF6B6B; color: white; padding: 10px 20px; border: 1px solid #333; border-radius: 5px; font-weight: bold; margin-right: 10px; height: 40px; display: flex; align-items: center;">
                STOP
            </div>
            <div style="font-size: 20px; color: #555; margin-right: 10px;">⬅️</div>
    """
    
    for _, row in row2.iterrows():
        html_content += create_box(row)
        html_content += "<div style='font-size: 20px; color: #555; margin: 0 4px;'>⬅️</div>"
        
    # Potong panah terakhir di baris 2
    html_content = html_content.rsplit("<div style='font-size: 20px; color: #555; margin: 0 4px;'>⬅️</div>", 1)[0]

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
    st.markdown("""
    *   🟩 **Hijau**: Availability > 95% (Aman)
    *   🟨 **Kuning**: Availability 85% - 95% (Waspada)
    *   🟥 **Merah**: Availability < 85% (Kritis)
    """)
    
    # Render Diagram HTML
    html_diagram = draw_rbd_html(df_struktur)
    # Karena sekarang hanya ada 2 baris, kita bisa hilangkan scroll horizontal bawaan HTML jika muat
    components.html(html_diagram, height=250, scrolling=True)
    
    # Tampilkan Tabel Pendukung
    st.markdown("### 📊 Data Detail Sistem")
    st.dataframe(df_struktur[["ID", "Nama Sistem", "Availability"]].style.format({"Availability": "{:.2%}"}), 
                 use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
    st.info("Pastikan Sheet 'Struktur_RBD' sudah dibuat dan nama-namanya sesuai.")
