import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import comb, gamma
from scipy import stats
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="RBD Analyzer PLTU — RAM", page_icon="🔧", layout="wide")
st.title("🔧 RBD Analyzer PLTU — Standar RAM")
st.caption("Weibull reliability • 3 metrik RAM • Benchmark IVARA • Live dari Google Sheets")

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
    df_event = pd.DataFrame(sh.worksheet("Event_Log").get_all_records())
    df_obs = pd.DataFrame(sh.worksheet("Observasi").get_all_records())
    df_konfig = pd.DataFrame(sh.worksheet("Konfigurasi_Grup").get_all_records())
    return df_event, df_obs, df_konfig

# ============================================================
# HITUNG TTF & TTR PER EQUIPMENT
# ============================================================
def parse_dt(s):
    """Parse date string fleksibel."""
    if pd.isna(s) or s == "": return pd.NaT
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
                "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try: return pd.to_datetime(s, format=fmt)
        except: continue
    return pd.to_datetime(s, errors="coerce")

def hitung_ttf_ttr(df_event):
    """Hitung list TTF (menit) dan TTR (menit) per equipment."""
    df = df_event.copy()
    df["Waktu Mulai Operasi"] = df["Waktu Mulai Operasi"].apply(parse_dt)
    df["Tanggal Gagal"] = df["Tanggal Gagal"].apply(parse_dt)
    df["Tanggal Selesai Repair"] = df["Tanggal Selesai Repair"].apply(parse_dt)
    df = df[df["Kategori"].str.strip().str.lower() == "corrective"].copy()

    hasil = {}
    for eq, grp in df.groupby("Equipment"):
        grp = grp.sort_values("Tanggal Gagal")
        ttf_list = []
        ttr_list = []
        for _, row in grp.iterrows():
            if pd.notna(row["Waktu Mulai Operasi"]) and pd.notna(row["Tanggal Gagal"]):
                ttf = (row["Tanggal Gagal"] - row["Waktu Mulai Operasi"]).total_seconds() / 60
                if ttf > 0: ttf_list.append(ttf)
            if pd.notna(row["Tanggal Gagal"]) and pd.notna(row["Tanggal Selesai Repair"]):
                ttr = (row["Tanggal Selesai Repair"] - row["Tanggal Gagal"]).total_seconds() / 60
                if ttr > 0: ttr_list.append(ttr)
        hasil[eq] = {"TTF": ttf_list, "TTR": ttr_list}
    return hasil

# ============================================================
# FIT WEIBULL
# ============================================================
def fit_weibull(data_menit):
    """Fit Weibull 2-parameter. Return beta, theta, MTTF (menit), atau None kalau data kurang."""
    data = np.array([x for x in data_menit if x > 0 and not np.isnan(x)])
    if len(data) < 2:
        return None
    try:
        beta, loc, theta = stats.weibull_min.fit(data, floc=0)
        mttf = theta * gamma(1 + 1/beta)
        return {"beta": beta, "theta": theta, "mttf_menit": mttf, "n_data": len(data)}
    except Exception:
        return None

# ============================================================
# METRIK RAM
# ============================================================
def hitung_ram(ttf_data, ttr_data):
    """Hitung RAM dari data TTF & TTR."""
    fit_ttf = fit_weibull(ttf_data)
    fit_ttr = fit_weibull(ttr_data)
    if not fit_ttf:
        return None

    beta_f = fit_ttf["beta"]
    theta_f = fit_ttf["theta"]
    mttf = fit_ttf["mttf_menit"]

    # MTTR: pakai rata-rata aktual (lebih simple dari fit Weibull untuk repair)
    mttr = float(np.mean(ttr_data)) if len(ttr_data) > 0 else 0

    # Reliability R(t) — 1 tahun = 525,600 menit
    t_1yr = 525600
    R_1yr = np.exp(-(t_1yr / theta_f) ** beta_f)

    # Availability inherent
    A = mttf / (mttf + mttr) if (mttf + mttr) > 0 else 0

    # Maintainability H(t) pada t = MTTR
    if fit_ttr:
        beta_r = fit_ttr["beta"]
        theta_r = fit_ttr["theta"]
        H_at_mttr = 1 - np.exp(-(mttr / theta_r) ** beta_r)
    else:
        H_at_mttr = 1 - np.exp(-1)  # fallback: asumsi eksponensial

    # Klasifikasi phase berdasarkan beta_f
    if beta_f < 0.95:
        phase = "Infant Mortality (β<1) — defect manufaktur/QC"
    elif beta_f < 1.05:
        phase = "Random Failure (β≈1) — gunakan redundansi/spare"
    else:
        phase = "Wear-out (β>1) — lakukan preventive maintenance"

    return {
        "beta_TTF": beta_f, "theta_TTF": theta_f, "MTTF_menit": mttf,
        "MTTR_menit": mttr,
        "R_1tahun": R_1yr,
        "Availability": A,
        "Maintainability": H_at_mttr,
        "Phase": phase,
        "n_failure": len(ttf_data),
    }

# ============================================================
# SIDEBAR
# ============================================================
try:
    spreadsheet_id = st.secrets["GSHEET_SPREADSHEET_ID"]
except Exception:
    st.error("❌ `GSHEET_SPREADSHEET_ID` tidak ditemukan di Secrets.")
    st.stop()

with st.sidebar:
    st.header("⚙️ Kontrol")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.markdown("---")

    try:
        df_event, df_obs, df_konfig = load_data(spreadsheet_id)
    except Exception as e:
        st.error(f"❌ Error: {e}"); st.stop()

    df_konfig_edit = st.data_editor(
        df_konfig[["Grup", "Tipe", "k", "n"]], num_rows="dynamic",
        use_container_width=True, hide_index=True, key="konfig_editor")

    planned_outage_hari = st.number_input("Planned outage (hari/tahun)",
                                          min_value=0, max_value=90, value=30)
    common_cause_beta = st.slider("Common cause β", 0.0, 0.5, 0.10, 0.01)

# ============================================================
# HITUNG SEMUA
# ============================================================
ttf_ttr_data = hitung_ttf_ttr(df_event)

hasil_komp = []
for eq, data in ttf_ttr_data.items():
    ram = hitung_ram(data["TTF"], data["TTR"])
    if ram:
        ram["Equipment"] = eq
        hasil_komp.append(ram)

if not hasil_komp:
    st.warning("⚠️ Belum cukup data untuk fitting Weibull (butuh minimal 2 event per equipment).")
    st.stop()

df_komp = pd.DataFrame(hasil_komp)

# Grup availability
grup_avail = {}
for _, g in df_konfig_edit.iterrows():
    nama = str(g["Grup"]).strip(); tipe = str(g["Tipe"]).strip()
    try: k = int(float(g["k"])); n = int(float(g["n"]))
    except: k, n = 1, 1
    A_members = df_komp[df_komp["Equipment"].str.startswith(nama, na=False)]["Availability"].values
    if len(A_members) == 0: A_members = df_komp["Availability"].values

    if tipe == "Series":
        A_g = float(np.prod(A_members))
    elif tipe == "Parallel":
        A_indep = 1 - float(np.prod(1 - A_members))
        A_single = float(A_members[0]) if len(A_members) > 0 else 1.0
        A_g = A_indep * (1 - common_cause_beta) + A_single * common_cause_beta
    elif tipe == "kooN":
        A_pad = np.ones(n) * (A_members[0] if len(A_members) > 0 else 1.0)
        A_pad[:len(A_members)] = A_members[:n]
        A_indep = sum(comb(n, i) * A_pad[0]**i * (1 - A_pad[0])**(n - i) for i in range(k, n + 1))
        A_single = A_pad[0]
        A_g = A_indep * (1 - common_cause_beta) + A_single * common_cause_beta
    else: A_g = 0.0
    grup_avail[nama] = A_g

urutan_sistem = df_konfig_edit["Grup"].astype(str).str.strip().tolist()
A_unplanned = float(np.prod([grup_avail[g] for g in urutan_sistem]))
A_total = A_unplanned * (1 - planned_outage_hari / 365)

# ============================================================
# DASHBOARD 3 METRIK RAM (per equipment, pilih)
# ============================================================
st.header("📊 3 Metrik RAM (Standar IVARA)")

eq_pilih = st.selectbox("Pilih equipment:", df_komp["Equipment"].tolist())
row = df_komp[df_komp["Equipment"] == eq_pilih].iloc[0]

c1, c2, c3 = st.columns(3)
# Reliability dengan warna
delta_r = (row["R_1tahun"] - 0.50) * 100
c1.metric("Reliability R(1 tahun)", f"{row['R_1tahun']*100:.2f} %",
          delta=f"{delta_r:+.1f}% vs 50%",
          delta_color="normal" if row["R_1tahun"] >= 0.50 else "inverse")
c2.metric("Availability (Inherent)", f"{row['Availability']*100:.2f} %",
          delta=f"{(row['Availability']-0.95)*100:+.1f}% vs 95%",
          delta_color="normal" if row["Availability"] >= 0.95 else "inverse")
c3.metric("Maintainability H(MTTR)", f"{row['Maintainability']*100:.2f} %",
          delta=f"{(row['Maintainability']-0.80)*100:+.1f}% vs 80%",
          delta_color="normal" if row["Maintainability"] >= 0.80 else "inverse")

st.caption(f"β_TTF = {row['beta_TTF']:.3f} · θ_TTF = {row['theta_TTF']:.0f} menit · "
           f"MTTF = {row['MTTF_menit']:.0f} menit ({row['MTTF_menit']/1440:.1f} hari) · "
           f"MTTR = {row['MTTR_menit']:.0f} menit ({row['MTTR_menit']/60:.1f} jam) · "
           f"n_failure = {row['n_failure']}")

st.info(f"🔍 **Phase deteksi**: {row['Phase']}")

# ============================================================
# TABEL RINGKASAN SEMUA KOMPONEN
# ============================================================
st.header("📋 Ringkasan Semua Komponen")
df_show = df_komp[["Equipment", "beta_TTF", "MTTF_menit", "MTTR_menit",
                    "R_1tahun", "Availability", "Maintainability", "Phase"]].copy()
df_show["MTTF (hari)"] = (df_show["MTTF_menit"] / 1440).round(1)
df_show["MTTR (jam)"] = (df_show["MTTR_menit"] / 60).round(1)
df_show["R(1thn) %"] = (df_show["R_1tahun"] * 100).round(2)
df_show["A %"] = (df_show["Availability"] * 100).round(2)
df_show["H %"] = (df_show["Maintainability"] * 100).round(2)
df_show["β"] = df_show["beta_TTF"].round(3)
df_show = df_show[["Equipment", "β", "MTTF (hari)", "MTTR (jam)",
                    "R(1thn) %", "A %", "H %", "Phase"]]
st.dataframe(df_show, use_container_width=True, hide_index=True)

# ============================================================
# GRAFIK WEIBULL
# ============================================================
st.header(f"📈 Distribusi Weibull — {eq_pilih}")

col1, col2 = st.columns(2)

with col1:
    # Survival function R(t)
    t_arr = np.linspace(0, max(8760*24*2, row["MTTF_menit"]*3), 200)  # 2 tahun
    R_arr = np.exp(-(t_arr / row["theta_TTF"]) ** row["beta_TTF"])
    fig1, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(t_arr / 1440, R_arr * 100, color="#3b82f6", linewidth=2)
    ax1.axhline(50, color="gray", linestyle="--", alpha=0.5)
    ax1.axvline(365, color="red", linestyle=":", alpha=0.7, label="1 tahun")
    ax1.set_xlabel("Waktu (hari)")
    ax1.set_ylabel("Reliability R(t) (%)")
    ax1.set_title("Kurva Survival R(t)")
    ax1.legend(); ax1.grid(alpha=0.3)
    plt.tight_layout(); st.pyplot(fig1)

with col2:
    # PDF Weibull
    pdf_arr = stats.weibull_min.pdf(t_arr, row["beta_TTF"], loc=0, scale=row["theta_TTF"])
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.plot(t_arr / 1440, pdf_arr, color="#10b981", linewidth=2)
    ax2.set_xlabel("Waktu (hari)")
    ax2.set_ylabel("Probability Density f(t)")
    ax2.set_title(f"PDF Weibull (β={row['beta_TTF']:.2f}, θ={row['theta_TTF']/1440:.0f} hari)")
    ax2.grid(alpha=0.3)
    plt.tight_layout(); st.pyplot(fig2)

# ============================================================
# AVAILABILITY SISTEM (RBD)
# ============================================================
st.header("🏭 Availability Sistem (RBD)")
c1, c2, c3 = st.columns(3)
c1.metric("A Unplanned", f"{A_unplanned*100:.2f} %")
c2.metric("A Total", f"{A_total*100:.2f} %")
c3.metric("Downtime Total", f"{(1-A_total)*8760:.0f} jam/thn")

st.subheader("📋 Availability per Grup")
df_grup_show = pd.DataFrame([
    {"Grup": g,
     "Tipe": df_konfig_edit[df_konfig_edit["Grup"].astype(str).str.strip() == g]["Tipe"].values[0],
     "Availability (%)": f"{grup_avail[g]*100:.4f}"}
    for g in urutan_sistem
])
st.dataframe(df_grup_show, use_container_width=True, hide_index=True)

# ============================================================
# DOWNLOAD
# ============================================================
st.header("⬇️ Download")
csv = df_komp.to_csv(index=False)
st.download_button("Download hasil RAM (CSV)", csv,
                   file_name="ram_hasil.csv", mime="text/csv")
