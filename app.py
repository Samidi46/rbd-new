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
    
    df_struktur = pd.DataFrame(sh.worksheet("Struktur_RBD").get_all_records())
    
    # Simulasi Data RI (Untuk warna)
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
# FUNGSI WARNA
# ============================================================
def get_color(ri):
    if ri >= 0.81: return '#4b8c36'  # Hijau Gelap
    elif ri >= 0.61: return '#92d050' # Hijau Muda
    elif ri >= 0.41: return '#ffff00' # Kuning
    elif ri >= 0.21: return '#ff0000' # Merah
    else: return '#000000'            # Hitam

def get_text_color(ri):
    return 'black' if 0.41 <= ri < 0.81 else 'white'

# ============================================================
# RENDER DIAGRAM RBD UTAMA
# ============================================================
def draw_main_rbd(df):
    row1 = df[df["ID"] <= 12].sort_values("ID")
    row2 = df[df["ID"] > 12].sort_values("ID", ascending=False) 

    html = f"""<div style="display: flex; flex-direction: column; align-items: center; overflow-x: auto; padding: 10px; background-color: #f9f9f9; border-radius: 10px; min-width: max-content;">
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
    spreadsheet_id = st.secrets["GSHEET_SPREADSHEET_ID"]
    df_struktur = load_data(spreadsheet_id)
    
    st.title("⚡ RBD Visual Dashboard — PLTU")
    st.caption("Klik pada menu di bawah untuk melihat detail analisis sub-sistem.")
    
    st.markdown("""
    🟩 **> 0.80** (Very Good) | 🟩 **0.61-0.80** (Good) | 🟨 **0.41-0.60** (Quite) | 🟥 **0.21-0.40** (Poor) | ⬛ **< 0.20** (Very Poor)
    """)
    
    html_diagram = draw_main_rbd(df_struktur)
    components.html(html_diagram, height=250, scrolling=True)
    
    st.divider()
    
    # --- NAVIGASI MENU (HYBRID: AKTIF & COMING SOON) ---
    st.subheader("📌 Pilih Sistem untuk Analisis Detail")
    
    # CSS untuk tombol
    st.markdown("""
    <style>
        .nav-link { display: block; padding: 8px 12px; margin: 4px 0; background-color: #f0f2f6; border-radius: 5px; text-decoration: none; color: #31333F; font-weight: 500; transition: background 0.2s; }
        .nav-link:hover { background-color: #e0e4eb; color: #FF4B4B; }
        .nav-disabled { display: block; padding: 8px 12px; margin: 4px 0; background-color: #e9ecef; border-radius: 5px; color: #a0a0a0; font-weight: 500; cursor: not-allowed; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    
    with col1:
        # YANG SUDAH ADA FILE-NYA (BISA DIKLIK)
        st.markdown('<a href="/FireProt" target="_self" class="nav-link">🔥 1. Fire Protection System</a>', unsafe_allow_html=True)
        
        # YANG BELUM ADA FILE-NYA (COMING SOON)
        st.markdown('<div class="nav-disabled">⚙️ 2. Proses Protection (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">⚡ 3. Electrical Protection (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">🔋 4. Emergency Power (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">🎛️ 5. Electrical & Control (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">💧 6. Circulating Water (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">❄️ 7. Closed Cooling Water (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">💨 8. General Air Control (Soon)</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="nav-disabled">🧪 9. Water Treatment (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">🛢️ 10. Fuel Oil System (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">🔥 11. Auxiliary Boiler (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">💧 12. Condensate System (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">🚰 13. Feedwater System (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">♨️ 14. Heat Generation (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">⛏️ 15. Coal Handling (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">🏭 16. Bunker & Pulverizing (Soon)</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="nav-disabled">🌬️ 17. Combustion Air (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">🔥 18. Boiler Firing (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">🗑️ 19. Ash & Slag Removal (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">☁️ 20. Steam System (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">⚡ 21. Steam Turbine (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">🔌 22. Generator Plant (Soon)</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-disabled">⚡ 23. Transmission (Soon)</div>', unsafe_allow_html=True)

    st.divider()
    
    # Tabel Data Detail
    st.markdown("### 📊 Data Detail Sistem")
    df_show = df_struktur[["ID", "Nama Sistem", "RI"]].copy()
    df_show["RI"] = (df_show["RI"] * 100).round(1)
    st.dataframe(df_show.style.format({"RI": "{:.1f}%"}), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
