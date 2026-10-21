import streamlit as st
import streamlit.components.v1 as components
from utils.data_loader import load_data, get_color, get_text_color

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Fire Protection RBD", layout="wide")
st.title("🔥 Analisis Sub-Sistem: Fire Protection System")

# --- LOAD DATA ---
spreadsheet_id = st.secrets["GSHEET_SPREADSHEET_ID"]
# Kita hanya butuh df_subs (tabel detail sub-sistem)
_, df_subs = load_data(spreadsheet_id)

# --- FILTER DATA ---
# Di sini kita filter berdasarkan Sistem_ID = 1
SISTEM_ID = 1 
df_filter = df_subs[df_subs["Sistem_ID"] == SISTEM_ID]

# --- RENDER DIAGRAM ---
if df_filter.empty:
    st.warning("⚠️ Detail RBD untuk sistem ini belum tersedia di database Google Sheets Anda.")
else:
    # Susun HTML untuk diagram sub-sistem
    html = f"""<div style="display: flex; flex-direction: column; align-items: center; padding: 20px; background-color: #e6f2ff; border-radius: 10px; min-width: max-content;">
        <div style="display: flex; flex-direction: row; align-items: center;">
            <div style="font-size: 18px; color: #555; margin-right: 5px;">START ➡️</div>"""
            
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
        
    # Hapus panah terakhir dan tambahkan STOP
    html = html.rsplit("<div style='font-size: 18px; color: #555; margin: 0 5px;'>➡️</div>", 1)[0]
    html += "<div style='font-size: 18px; color: #555; margin-left: 5px;'>STOP</div></div></div>"
    
    # Tampilkan Diagram
    components.html(html, height=200, scrolling=True)
    
    # Tampilkan Tabel Data
    st.markdown("### 📋 Data Komponen")
    st.dataframe(df_filter[["Nama_Komponen", "Reliability", "Availability"]], use_container_width=True, hide_index=True)
