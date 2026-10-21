import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import comb
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="RBD Analyzer PLTU", page_icon="🔧", layout="wide")
st.title("🔧 RBD Analyzer PLTU")
st.caption("Data langsung dari Google Sheets — edit di Sheets, klik Refresh di sini.")

# ============================================================
# KONEKSI GOOGLE SHEETS
# ============================================================
@st.cache_resource
def get_gsheet_client():
    """Buat koneksi ke Google Sheets (di-cache, hanya sekali per session)."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Gagal koneksi ke Google: {e}")
        st.info("Cek Secrets Anda di Streamlit Cloud Settings.")
        st.stop()

@st.cache_data(ttl=60)
def load_data(spreadsheet_id: str):
    """Baca semua sheet. Cache 60 detik, lalu auto-refresh."""
    client = get_gsheet_client()
    sh = client.open_by_key(spreadsheet_id)

    ws_event = sh.worksheet("Event_Log").get_all_records()
    ws_obs = sh.worksheet("Observasi").get_all_records()
    ws_konfig = sh.worksheet("Konfigurasi_Grup").get_all_records()

    df_event = pd.DataFrame(ws_event)
    df_obs = pd.DataFrame(ws_obs)
    df_konfig = pd.DataFrame(ws_konfig)

    # Validasi kolom wajib
    wajib_event = ["Equipment", "Durasi Repair (jam)", "Kategori"]
    wajib_konfig = ["Grup", "Tipe", "k", "n"]
    wajib_obs = ["Total Jam Operasi"]

    missing = []
    for col in wajib_event:
        if col not in df_event.columns:
            missing.append(f"Event_Log → {col}")
    for col in wajib_konfig:
        if col not in df_konfig.columns:
            missing.append(f"Konfigurasi_Grup → {col}")
    for col in wajib_obs:
        if col not in df_obs.columns:
            missing.append(f"Observasi → {col}")

    if missing:
        st.error(f"❌ Kolom tidak ditemukan: {missing}")
        st.stop()

    return df_event, df_obs, df_konfig

# ============================================================
# KALKULASI LAMBDA & MTTR DARI EVENT LOG
# ============================================================
def hitung_lambda_mttr(df_event, total_jam_operasi):
    """Hitung lambda per tahun & MTTR per equipment dari raw event log."""
    # Filter hanya Corrective (bukan Planned)
    df_corr = df_event[df_event["Kategori"].str.strip().str.lower() == "corrective"].copy()
    df_corr["Durasi Repair (jam)"] = pd.to_numeric(
        df_corr["Durasi Repair (jam)"], errors="coerce").fillna(0)

    total_tahun = total_jam_operasi / 8760 if total_jam_operasi > 0 else 1

    hasil = []
    for eq, grp in df_corr.groupby("Equipment"):
        n_fail = len(grp)
        total_repair = grp["Durasi Repair (jam)"].sum()
        mttr = total_repair / n_fail if n_fail > 0 else 0
        lam = n_fail / total_tahun if total_tahun > 0 else 0
        A = (1 / lam) / ((1 / lam) + (mttr / 8760)) if lam > 0 else 1.0
        hasil.append({
            "Equipment": eq,
            "Jumlah Failure": n_fail,
            "Total Repair (jam)": total_repair,
            "MTTR (jam)": mttr,
            "Lambda (per tahun)": lam,
            "Availability": A,
        })
    return pd.DataFrame(hasil)

# ============================================================
# SIDEBAR & KONTROL
# ============================================================
try:
    spreadsheet_id = st.secrets["GSHEET_SPREADSHEET_ID"]
except Exception:
    st.error("❌ `GSHEET_SPREADSHEET_ID` tidak ditemukan di Secrets.")
    st.stop()

with st.sidebar:
    st.header("⚙️ Kontrol")
    if st.button("🔄 Refresh Data dari Google Sheets", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.header("📋 Konfigurasi RBD")

    try:
        df_event, df_obs, df_konfig = load_data(spreadsheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ Spreadsheet tidak ditemukan. Cek ID & pastikan sudah di-share ke service account.")
        st.stop()
    except gspread.exceptions.WorksheetNotFound as e:
        st.error(f"❌ Worksheet tidak ditemukan: {e}. Pastikan nama sheet: Event_Log, Observasi, Konfigurasi_Grup.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        st.stop()

    # Total jam operasi dari sheet Observasi
    try:
        total_jam_opsi = float(df_obs["Total Jam Operasi"].iloc[0])
    except Exception:
        total_jam_opsi = 16000.0
        st.warning(f"⚠️ Total Jam Operasi tidak terbaca, pakai default {total_jam_opsi}")

    st.caption(f"📊 Total Jam Operasi (observasi): **{total_jam_opsi:,.0f} jam** "
               f"({total_jam_opsi/8760:.2f} tahun)")

    # Konfigurasi grup — bisa diedit user (override dari sheet)
    df_konfig_edit = st.data_editor(
        df_konfig[["Grup", "Tipe", "k", "n"]],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="konfig_editor",
    )

    st.markdown("---")
    st.subheader("🎯 Faktor Realistis")
    planned_outage_hari = st.number_input("Planned outage (hari/tahun)",
                                          min_value=0, max_value=90, value=30)
    common_cause_beta = st.slider("Common cause factor β", 0.0, 0.5, 0.10, 0.01,
                                   help="Fraksi kegagalan redundan akibat common cause")

# ============================================================
# HITUNG & TAMPILKAN
# ============================================================
df_komponen = hitung_lambda_mttr(df_event, total_jam_opsi)

# Per grup (dengan common cause correction)
grup_avail = {}
for _, g in df_konfig_edit.iterrows():
    nama = str(g["Grup"]).strip()
    tipe = str(g["Tipe"]).strip()
    try:
        k = int(float(g["k"]))
        n = int(float(g["n"]))
    except Exception:
        k, n = 1, 1

    A_members = df_komponen[df_komponen["Equipment"].str.startswith(nama, na=False)]["Availability"].values
    if len(A_members) == 0:
        A_members = df_komponen["Availability"].values  # fallback

    if tipe == "Series":
        A_g = float(np.prod(A_members))
    elif tipe == "Parallel":
        A_indep = 1 - float(np.prod(1 - A_members))
        A_single = float(A_members[0]) if len(A_members) > 0 else 1.0
        A_g = A_indep * (1 - common_cause_beta) + A_single * common_cause_beta
    elif tipe == "kooN":
        A_pad = np.ones(n) * (A_members[0] if len(A_members) > 0 else 1.0)
        A_pad[:len(A_members)] = A_members[:n]
        A_indep = sum(comb(n, i) * A_pad[0]**i * (1 - A_pad[0])**(n - i)
                      for i in range(k, n + 1))
        A_single = A_pad[0]
        A_g = A_indep * (1 - common_cause_beta) + A_single * common_cause_beta
    else:
        A_g = 0.0
    grup_avail[nama] = A_g

urutan_sistem = df_konfig_edit["Grup"].astype(str).str.strip().tolist()
A_unplanned = float(np.prod([grup_avail[g] for g in urutan_sistem]))
A_total = A_unplanned * (1 - planned_outage_hari / 365)

# Metric cards
c1, c2, c3 = st.columns(3)
c1.metric("Availability (Unplanned only)", f"{A_unplanned*100:.2f} %")
c2.metric("Availability Total", f"{A_total*100:.2f} %")
downtime_unplanned = (1 - A_unplanned) * 8760
downtime_total = (1 - A_total) * 8760
c3.metric("Downtime Total", f"{downtime_total:.0f} jam/tahun")
st.caption(f"Unplanned: {downtime_unplanned:.1f} jam/thn · Planned: {planned_outage_hari*24:.0f} jam/thn · β = {common_cause_beta}")

# Data mentah per equipment (hasil rekap dari Event_Log)
st.subheader("📊 Data Failure Rate per Equipment (dihitung dari Event_Log)")
df_show = df_komponen.copy()
df_show["Lambda (per tahun)"] = df_show["Lambda (per tahun)"].round(3)
df_show["MTTR (jam)"] = df_show["MTTR (jam)"].round(1)
df_show["Availability (%)"] = (df_show["Availability"] * 100).round(3)
st.dataframe(df_show, use_container_width=True, hide_index=True)

# Grafik ranking
st.subheader("📈 Ranking Komponen (paling critical di bawah)")
df_rank = df_komponen.sort_values("Availability")
fig, ax = plt.subplots(figsize=(10, max(4, len(df_rank) * 0.4)))
ax.barh(df_rank["Equipment"], df_rank["Availability"] * 100, color="#3b82f6")
ax.set_xlabel("Availability (%)")
ax.set_title("Semakin rendah = semakin critical")
plt.tight_layout()
st.pyplot(fig)

# Per grup
st.subheader("📋 Availability per Grup RBD")
df_grup_show = pd.DataFrame([
    {"Grup": g, "Tipe": df_konfig_edit[df_konfig_edit["Grup"].astype(str).str.strip() == g]["Tipe"].values[0] if len(df_konfig_edit[df_konfig_edit["Grup"].astype(str).str.strip() == g]) > 0 else "?",
     "Availability (%)": f"{grup_avail[g]*100:.4f}"}
    for g in urutan_sistem
])
st.dataframe(df_grup_show, use_container_width=True, hide_index=True)

# Kurva R(t)
st.subheader("📉 Kurva Reliability R(t) Sistem (0–365 hari)")
def R_sistem(t_jam):
    R_g = {}
    for _, g in df_konfig_edit.iterrows():
        nama = str(g["Grup"]).strip()
        tipe = str(g["Tipe"]).strip()
        try:
            k = int(float(g["k"])); n = int(float(g["n"]))
        except Exception:
            k, n = 1, 1
        sub = df_komponen[df_komponen["Equipment"].str.startswith(nama, na=False)]
        if len(sub) == 0:
            sub = df_komponen
        R_ind = np.exp(-(sub["Lambda (per tahun)"] / 8760) * t_jam).values
        if tipe == "Series":
            R_g[nama] = float(np.prod(R_ind))
        elif tipe == "Parallel":
            R_g[nama] = float(1 - np.prod(1 - R_ind))
        elif tipe == "kooN":
            R_pad = np.ones(n) * (R_ind[0] if len(R_ind) else 1.0)
            R_pad[:len(R_ind)] = R_ind[:n]
            R_g[nama] = sum(comb(n, i) * R_pad[0]**i * (1 - R_pad[0])**(n - i)
                            for i in range(k, n + 1))
        else:
            R_g[nama] = 0.0
    return float(np.prod([R_g[g] for g in urutan_sistem]))

t_arr = np.linspace(0, 8760, 100)
R_arr = [R_sistem(t) * 100 for t in t_arr]
fig2, ax2 = plt.subplots(figsize=(10, 4))
ax2.plot(t_arr / 24, R_arr, color="#10b981", linewidth=2)
ax2.set_xlabel("Waktu (hari)")
ax2.set_ylabel("R(t) (%)")
ax2.set_title("Probabilitas tidak ada kegagalan sampai waktu t")
ax2.grid(alpha=0.3)
plt.tight_layout()
st.pyplot(fig2)

# Download
st.subheader("⬇️ Download Hasil")
csv = df_komponen.to_csv(index=False)
st.download_button("Download hasil komponen (CSV)", csv,
                   file_name="rbd_hasil.csv", mime="text/csv")
