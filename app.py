import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials

# ============================================================
# KONFIGURASI HALAMAN
# ============================================================
st.set_page_config(page_title="RBD PLTU Dashboard", layout="wide")

# ============================================================
# KONEKSI GOOGLE SHEETS (BACKEND)
# ============================================================
@st.cache_resource
def get_gsheet_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            key = creds_dict["private_key"]
            if "\\n" in key: key = key.replace("\\n", "\n")
            creds_dict["private_key"] = key
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Gagal koneksi ke Google: {e}")
        st.stop()

@st.cache_data(ttl=60)
def load_data(spreadsheet_id: str):
    client = get_gsheet_client()
    sh = client.open_by_key(spreadsheet_id)
    
    # 1. Load Data Struktur RBD
    df_struktur = pd.DataFrame(sh.worksheet("Struktur_RBD").get_all_records())
    
    # --- SIMULASI DATA (Agar warna bervariasi saat testing) ---
    # Nanti bagian ini bisa diganti dengan perhitungan Weibull asli
    dummy_data = {
        "FireProt": {"RI": 0.99}, "ProsesProt": {"RI": 0.85}, "ElecProt": {"RI": 0.75}, 
        "EmergencyPower": {"RI": 0.55}, "ElecControl": {"RI": 0.90}, "CW": {"RI": 0.15}, 
        "CCW": {"RI": 0.35}, "AirControl": {"RI": 0.95}, "CWT": {"RI": 0.99}, 
        "FuelOil": {"RI": 0.85}, "AuxBoiler": {"RI": 0.70}, "Condensate": {"RI": 0.99}, 
        "Feedwater": {"RI": 0.45}, "HeatGen": {"RI": 0.88}, "CoalHandling": {"RI": 0.65}, 
        "Bunker": {"RI": 0.92}, "CombustionAir": {"RI": 0.85}, "BoilerFiring": {"RI": 0.95},
        "AshSlag": {"RI": 0.70}, "Steam": {"RI": 0.99}, "Turbine": {"RI": 0.25}, 
        "Generator": {"RI": 0.85}, "Transmission": {"RI": 0.99}
    }
    df_struktur["RI"] = df_struktur["Equipment_Group"].map(lambda x: dummy_data.get(x, {"RI": 0.99})["RI"])
    
    return df_struktur

# ============================================================
# FUNGSI WARNA (STANDAR IVARA)
# ============================================================
def get_color(ri):
    if ri >= 0.81: return '#4b8c36'  # Hijau Gelap (Very Good)
    elif ri >= 0.61: return '#92d050' # Hijau Muda (Good)
    elif ri >= 0.41: return '#ffff00' # Kuning (Quite)
    elif ri >= 0.21: return '#ff0000' # Merah (Poor)
    else: return '#000000'            # Hitam (Very Poor)

def get_text_color(ri):
    return 'black' if 0.41 <= ri < 0.81 else 'white'

# ============================================================
# RENDER DIAGRAM RBD (HTML/CSS)
# ============================================================
def draw_main_rbd(df):
    row1 = df[df["ID"] <= 12].sort_values("ID")
    row2 = df[df["ID"] > 12].sort_values("ID", ascending=False) 

    html = f"""<div style="display: flex; flex-direction: column; align-items: center; overflow-x: auto; padding: 10px; background-color: #f9f9f9; border-radius: 10px; min-width: max-content;">
        <!-- BARIS 1 -->
        <div style="display: flex; flex-direction: row; align-items: center; margin-bottom: 15px;">
            <div style="background-color: #90EE90; padding: 10px 15px; border: 1px solid #333; border-radius: 5px; font-weight: bold; margin-right: 10px; height: 40px; display: flex; align-items: center;">START</div>
            <div style="font-size: 18px; color: #555; margin-right: 5px;">➡️</div>"""
            
    for _, row in row1.iterrows():
        color = get_color(row['RI'])
        text_color = get_text_color(row['RI'])
        html += f"""
        <div style="background-color: {color}; color: {text_color}; border: 1px solid #333; border-radius: 5px; padding: 6px; width: 140px; height: 60px; text-align: center; font-family: Arial, sans-serif; font-size: 11px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2); margin: 0 2px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <strong style="font-size: 11px; margin-bottom: 2px;">{row['ID']}. {row['Nama Sistem']}</strong>
            <span style="font-weight: bold; font-size: 12px;">R: {row['RI']*100:.1f}%</span>
        </div>
        <div style="font-size: 18px; color: #555; margin: 0 2px;">➡️</div>"""
        
    html = html.rsplit("<div style='font-size: 18px; color: #555; margin: 0 2px;'>➡️</div>", 1)[0]
    
    html += """</div>
        <!-- BARIS 2 -->
        <div style="display: flex; flex-direction: row; align-items: center;">
            <div style="background-color: #FF6B6B; color: white; padding: 10px 15px; border: 1px solid #333; border-radius: 5px; font-weight: bold; margin-right: 10px; height: 40px; display: flex; align-items: center;">STOP</div>
            <div style="font-size: 18px; color: #555; margin-right: 5px;">⬅️</div>"""
            
    for _, row in row2.iterrows():
        color = get_color(row['RI'])
        text_color = get_text_color(row['RI'])
        html += f"""
        <div style="background-color: {color}; color: {text_color}; border: 1px solid #333; border-radius: 5px; padding: 6px; width: 140px; height: 60px; text-align: center; font-family: Arial, sans-serif; font-size: 11px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2); margin: 0 2px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <strong style="font-size: 11px; margin-bottom: 2px;">{row['ID']}. {row['Nama Sistem']}</strong>
            <span style="font-weight: bold; font-size: 12px;">R: {row['RI']*100:.1f}%</span>
        </div>
        <div style="font-size: 18px; color: #555; margin: 0 2px;">⬅️</div>"""
        
    html = html.rsplit("<div style='font-size: 18px; color: #555; margin: 0 2px;'>⬅️</div>", 1)[0]
    html += "</div></div>"
    return html

# ============================================================
# MAIN APP
# ============================================================
try:
    # Load Data
    spreadsheet_id = st.secrets["GSHEET_SPREADSHEET_ID"]
    df_struktur = load_data(spreadsheet_id)
    
    # Header
    st.title("⚡ RBD Visual Dashboard — PLTU")
    st.caption("Klik pada menu di bawah untuk melihat detail analisis sub-sistem.")
    
    # Legenda Warna
    st.markdown("""
    🟩 **> 0.80** (Very Good) | 🟩 **0.61-0.80** (Good) | 🟨 **0.41-0.60** (Quite) | 🟥 **0.21-0.40** (Poor) | ⬛ **< 0.20** (Very Poor)
    """)
    
    # Render Diagram HTML
    html_diagram = draw_main_rbd(df_struktur)
    components.html(html_diagram, height=250, scrolling=True)
    
    st.divider()
    
    # --- NAVIGASI MENU (Menggunakan st.page_link) ---
    st.subheader("📌 Pilih Sistem untuk Analisis Detail")
    
    # Bagi menjadi 3 kolom agar rapi
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.page_link("pages/FireProt.py", label="1. Fire Protection System", icon="🔥")
        st.page_link("pages/ProsesProt.py", label="2. Proses Protection System", icon="⚙️")
        st.page_link("pages/ElecProt.py", label="3. Electrical Protection System", icon="⚡")
        st.page_link("pages/EmergencyPower.py", label="4. Emergency Power Supply", icon="🔋")
        st.page_link("pages/ElecControl.py", label="5. Electrical & Control", icon="🎛️")
        st.page_link("pages/CW.py", label="6. Circulating Water System", icon="💧")
        st.page_link("pages/CCW.py", label="7. Closed Cooling Water", icon="❄️")
        st.page_link("pages/AirControl.py", label="8. General Air Control", icon="💨")

    with col2:
        st.page_link("pages/CWT.py", label="9. Circulating Water Treatment", icon="🧪")
        st.page_link("pages/FuelOil.py", label="10. Fuel Oil System", icon="🛢️")
        st.page_link("pages/AuxBoiler.py", label="11. Auxiliary Boiler", icon="🔥")
        st.page_link("pages/Condensate.py", label="12. Condensate System", icon="💧")
        st.page_link("pages/Feedwater.py", label="13. Feedwater System", icon="🚰")
        st.page_link("pages/HeatGen.py", label="14. Heat Generation Pressure", icon="♨️")
        st.page_link("pages/CoalHandling.py", label="15. Solid Fuel/Coal Handling", icon="⛏️")
        st.page_link("pages/Bunker.py", label="16. Bunker, Feeder & Pulverizing", icon="🏭")

    with col3:
        st.page_link("pages/CombustionAir.py", label="17. Combustion Air Flue Gas", icon="🌬️")
        st.page_link("pages/BoilerFiring.py", label="18. Main Boiler Firing", icon="🔥")
        st.page_link("pages/AshSlag.py", label="19. Ash & Slag Removal", icon="🗑️")
        st.page_link("pages/Steam.py", label="20. Steam System", icon="☁️")
        st.page_link("pages/Turbine.py", label="21. Steam Turbine System", icon="⚡")
        st.page_link("pages/Generator.py", label="22. Generator Plant System", icon="🔌")
        st.page_link("pages/Transmission.py", label="23. Power Transmission System", icon="⚡")

    st.divider()
    
    # Tabel Data Detail
    st.markdown("### 📊 Data Detail Sistem")
    df_show = df_struktur[["ID", "Nama Sistem", "RI"]].copy()
    df_show["RI"] = (df_show["RI"] * 100).round(1)
    st.dataframe(df_show.style.format({"RI": "{:.1f}%"}), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
    st.info("Pastikan Sheet 'Struktur_RBD' sudah dibuat dan ID/Equipment_Group sesuai.")
