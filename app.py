import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="RBD PLTU Dashboard", layout="wide")

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
    
    # Load Data Utama
    df_struktur = pd.DataFrame(sh.worksheet("Struktur_RBD").get_all_records())
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
    
    # Load Data Sub-Sistem
    try:
        df_subs = pd.DataFrame(sh.worksheet("Detail_Sub_Sistem").get_all_records())
    except:
        df_subs = pd.DataFrame(columns=["Sistem_ID", "Nama_Komponen", "Reliability", "Availability"])
        
    return df_struktur, df_subs

# ============================================================
# FUNGSI WARNA
# ============================================================
def get_color(ri):
    if ri >= 0.81: return '#4b8c36' # Hijau Gelap
    elif ri >= 0.61: return '#92d050' # Hijau Muda
    elif ri >= 0.41: return '#ffff00' # Kuning
    elif ri >= 0.21: return '#ff0000' # Merah
    else: return '#000000' # Hitam

def get_text_color(ri):
    return 'black' if 0.41 <= ri < 0.81 else 'white'

# ============================================================
# RENDER DIAGRAM UTAMA
# ============================================================
def draw_main_rbd(df):
    def create_clickable_box(row):
        ri = row['RI']
        color = get_color(ri)
        text_color = get_text_color(ri)
        # Link menggunakan query param ?sistem=ID
        link = f"?sistem={row['ID']}"
        
        return f"""
        <a href="{link}" target="_self" style="text-decoration: none;">
            <div style="
                background-color: {color}; color: {text_color}; border: 2px solid #333;
                border-radius: 5px; padding: 6px; width: 140px; height: 70px;
                text-align: center; font-family: Arial, sans-serif; font-size: 11px;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.3); margin: 0 4px;
                display: flex; flex-direction: column; justify-content: center; align-items: center;
                transition: transform 0.2s; cursor: pointer;
            " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                <strong style="font-size: 11px; margin-bottom: 2px;">{row['ID']}. {row['Nama Sistem']}</strong>
                <span style="font-weight: bold; font-size: 12px;">R: {ri*100:.1f}%</span>
            </div>
        </a>
        """

    row1 = df[df["ID"] <= 12].sort_values("ID")
    row2 = df[df["ID"] > 12].sort_values("ID", ascending=False) 

    # Gunakan padding yang cukup agar tidak terpotong
    html = f"""<div style="display: flex; flex-direction: column; align-items: center; overflow-x: auto; padding: 20px; background-color: #f9f9f9; border-radius: 10px; min-width: max-content;">
        <!-- BARIS 1 -->
        <div style="display: flex; flex-direction: row; align-items: center; margin-bottom: 20px;">
            <div style="background-color: #90EE90; padding: 10px 15px; border: 1px solid #333; border-radius: 5px; font-weight: bold; margin-right: 10px; height: 40px; display: flex; align-items: center;">START</div>
            <div style="font-size: 18px; color: #555; margin-right: 5px;">➡️</div>"""
    for _, row in row1.iterrows():
        html += create_clickable_box(row) + "<div style='font-size: 18px; color: #555; margin: 0 2px;'>➡️</div>"
    html = html.rsplit("<div style='font-size: 18px; color: #555; margin: 0 2px;'>➡️</div>", 1)[0]
    
    html += """</div>
        <!-- BARIS 2 -->
        <div style="display: flex; flex-direction: row; align-items: center;">
            <div style="background-color: #FF6B6B; color: white; padding: 10px 15px; border: 1px solid #333; border-radius: 5px; font-weight: bold; margin-right: 10px; height: 40px; display: flex; align-items: center;">STOP</div>
            <div style="font-size: 18px; color: #555; margin-right: 5px;">⬅️</div>"""
    for _, row in row2.iterrows():
        html += create_clickable_box(row) + "<div style='font-size: 18px; color: #555; margin: 0 2px;'>⬅️</div>"
    html = html.rsplit("<div style='font-size: 18px; color: #555; margin: 0 2px;'>⬅️</div>", 1)[0]
    
    html += "</div></div>"
    return html

# ============================================================
# RENDER SUB-DIAGRAM
# ============================================================
def draw_sub_rbd(sistem_id, nama_sistem, df_subs):
    df_filter = df_subs[df_subs["Sistem_ID"] == sistem_id]
    
    if df_filter.empty:
        return "<div style='padding: 40px; text-align: center; background: #ffe4e1; border-radius: 10px;'><h3>⚠️ Detail RBD untuk sistem ini belum tersedia.</h3></div>"

    html = f"""<div style="display: flex; flex-direction: column; align-items: center; padding: 20px; background-color: #e6f2ff; border-radius: 10px; min-width: max-content;">
        <h3 style="margin-bottom: 20px;">Detail RBD: {sistem_id}. {nama_sistem}</h3>
        <div style="display: flex; flex-direction: row; align-items: center;">
            <div style="font-size: 18px; color: #555; margin-right: 5px;">➡️</div>"""
            
    for _, row in df_filter.iterrows():
        ri = float(row['Reliability'])
        color = get_color(ri)
        text_color = get_text_color(ri)
        html += f"""
        <div style="background-color: {color}; color: {text_color}; border: 2px solid #333; border-radius: 5px; padding: 10px; width: 150px; height: 80px; text-align: center; font-family: Arial; margin: 0 10px; display: flex; flex-direction: column; justify-content: center; box-shadow: 3px 3px 8px rgba(0,0,0,0.2);">
            <strong style="font-size: 12px;">{row['Nama_Komponen']}</strong>
            <span style="font-weight: bold; margin-top: 5px;">R: {ri*100:.1f}%</span>
        </div>
        <div style="font-size: 18px; color: #555; margin: 0 5px;">➡️</div>"""
        
    html = html.rsplit("<div style='font-size: 18px; color: #555; margin: 0 5px;'>➡️</div>", 1)[0]
    html += "</div></div>"
    return html

# ============================================================
# MAIN APP LOGIC
# ============================================================
try:
    spreadsheet_id = st.secrets["GSHEET_SPREADSHEET_ID"]
    df_struktur, df_subs = load_data(spreadsheet_id)
    
    query_params = st.query_params
    sistem_id = query_params.get("sistem", None)
    
    if sistem_id is not None:
        # --- TAMPILAN SUB-SISTEM ---
        sistem_id = int(sistem_id)
        if sistem_id not in df_struktur["ID"].values:
            st.error("Sistem tidak ditemukan.")
            st.stop()
            
        row_sistem = df_struktur[df_struktur["ID"] == sistem_id].iloc[0]
        nama_sistem = row_sistem["Nama Sistem"]
        
        # Tombol Kembali dengan Hard Refresh
        if st.button("⬅️ Kembali ke Peta Utama", type="primary"):
            st.query_params.clear()
            st.rerun()
            
        st.subheader(f"🔍 Analisis Sub-Sistem: {nama_sistem}")
        html_sub = draw_sub_rbd(sistem_id, nama_sistem, df_subs)
        # Tinggi 300px cukup untuk sub-sistem
        components.html(html_sub, height=300, scrolling=True)
        
    else:
        # --- TAMPILAN UTAMA ---
        st.title("⚡ RBD Visual Dashboard — PLTU")
        st.caption("Klik pada kotak sistem untuk melihat detail sub-sistem.")
        
        st.markdown("""
        🟩 **> 0.80** (Very Good) | 🟩 **0.61-0.80** (Good) | 🟨 **0.41-0.60** (Quite) | 🟥 **0.21-0.40** (Poor) | ⬛ **< 0.20** (Very Poor)
        """)
        
        html_main = draw_main_rbd(df_struktur)
        # TINGGI DITAMBAH JADI 400 AGAR TIDAK TERPOTONG
        components.html(html_main, height=400, scrolling=True)
        
        # Tabel HANYA DIPANGGIL SEKALI DI SINI
        st.markdown("### 📊 Data Detail Sistem")
        df_show = df_struktur[["ID", "Nama Sistem", "RI"]].copy()
        df_show["RI"] = (df_show["RI"] * 100).round(1)
        st.dataframe(df_show.style.format({"RI": "{:.1f}%"}), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
