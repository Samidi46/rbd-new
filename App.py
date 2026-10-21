import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import comb

st.set_page_config(page_title="RBD Analyzer PLTU", page_icon="🔧", layout="wide")
st.title("🔧 RBD Analyzer PLTU")
st.caption("Analisis Reliability Block Diagram untuk Pembangkit Listrik")

# ============================================================
# SIDEBAR — INPUT
# ============================================================
with st.sidebar:
    st.header("1️⃣ Komponen")
    default_komponen = pd.DataFrame([
        {"Nama": "ID Fan A",    "Lambda/yr": 0.50, "MTTR (jam)": 8,  "Grup": "IDF"},
        {"Nama": "ID Fan B",    "Lambda/yr": 0.50, "MTTR (jam)": 8,  "Grup": "IDF"},
        {"Nama": "Water Wall",  "Lambda/yr": 0.05, "MTTR (jam)": 72, "Grup": "Boiler"},
        {"Nama": "Superheater", "Lambda/yr": 0.10, "MTTR (jam)": 48, "Grup": "Boiler"},
        {"Nama": "Reheater",    "Lambda/yr": 0.08, "MTTR (jam)": 48, "Grup": "Boiler"},
        {"Nama": "HP Turbine",  "Lambda/yr": 0.03, "MTTR (jam)": 96, "Grup": "Turbine"},
        {"Nama": "IP Turbine",  "Lambda/yr": 0.03, "MTTR (jam)": 96, "Grup": "Turbine"},
        {"Nama": "LP Turbine",  "Lambda/yr": 0.04, "MTTR (jam)": 96, "Grup": "Turbine"},
        {"Nama": "Generator",   "Lambda/yr": 0.05, "MTTR (jam)": 72, "Grup": "Turbine"},
        {"Nama": "BFP A",       "Lambda/yr": 0.40, "MTTR (jam)": 12, "Grup": "BFP"},
        {"Nama": "BFP B",       "Lambda/yr": 0.40, "MTTR (jam)": 12, "Grup": "BFP"},
        {"Nama": "BFP C",       "Lambda/yr": 0.40, "MTTR (jam)": 12, "Grup": "BFP"},
    ])
    df_komp = st.data_editor(default_komponen, num_rows="dynamic",
                             use_container_width=True, hide_index=True,
                             key="komp_editor")

    st.header("2️⃣ Grup RBD")
    default_grup = pd.DataFrame([
        {"Grup": "IDF",     "Tipe": "Parallel", "k": 1, "n": 2},
        {"Grup": "Boiler",  "Tipe": "Series",   "k": 1, "n": 1},
        {"Grup": "Turbine", "Tipe": "Series",   "k": 1, "n": 1},
        {"Grup": "BFP",     "Tipe": "kooN",     "k": 2, "n": 3},
    ])
    df_grup = st.data_editor(default_grup, num_rows="dynamic",
                             use_container_width=True, hide_index=True,
                             key="grup_editor")

    st.header("3️⃣ Faktor Realistis")
    planned_outage_hari = st.number_input("Planned outage (hari/tahun)",
                                          min_value=0, max_value=90, value=30)
    common_cause_beta = st.slider("Common cause factor β",
                                  0.0, 0.5, 0.10, 0.01,
                                  help="Pecahan kegagalan redundan yang disebabkan common cause")

    st.markdown("---")
    run = st.button("🚀 Hitung", type="primary", use_container_width=True)

# ============================================================
# KALKULASI
# ============================================================
def hitung_availability(lam_per_yr, mttr_jam):
    lam_jam = lam_per_yr / 8760
    mtbf = 1 / lam_jam
    A = mtbf / (mtbf + mttr_jam)
    return A, mtbf

if not run:
    st.info("👈 Atur input di sidebar, lalu klik **🚀 Hitung**")
    st.stop()

# Per komponen
data_komp = []
for _, row in df_komp.iterrows():
    A, mtbf = hitung_availability(row["Lambda/yr"], row["MTTR (jam)"])
    data_komp.append({
        "Nama": row["Nama"],
        "Grup": row["Grup"],
        "Lambda/yr": row["Lambda/yr"],
        "MTTR (jam)": row["MTTR (jam)"],
        "Availability": A,
        "MTBF (jam)": mtbf,
    })
df_hasil = pd.DataFrame(data_komp)

# Per grup (dengan koreksi common cause)
grup_avail = {}
for _, g in df_grup.iterrows():
    nama, tipe, k, n = g["Grup"], g["Tipe"], int(g["k"]), int(g["n"])
    A_members = df_hasil[df_hasil["Grup"] == nama]["Availability"].values

    if tipe == "Series":
        A_g = float(np.prod(A_members))
    elif tipe == "Parallel":
        A_indep = 1 - np.prod(1 - A_members)
        A_single = A_members[0] if len(A_members) > 0 else 1.0
        A_g = A_indep * (1 - common_cause_beta) + A_single * common_cause_beta
    elif tipe == "kooN":
        A_pad = np.ones(n) * (A_members[0] if len(A_members) > 0 else 1.0)
        A_pad[:len(A_members)] = A_members
        A_indep = sum(comb(n, i) * A_pad[0]**i * (1 - A_pad[0])**(n - i)
                      for i in range(k, n + 1))
        A_single = A_pad[0]
        A_g = A_indep * (1 - common_cause_beta) + A_single * common_cause_beta
    else:
        A_g = 0.0
    grup_avail[nama] = A_g

# Sistem
urutan_sistem = df_grup["Grup"].tolist()
A_unplanned = float(np.prod([grup_avail[g] for g in urutan_sistem]))

# Availability total dengan planned outage
A_total = A_unplanned * (1 - planned_outage_hari / 365)

# ============================================================
# TAMPILAN HASIL
# ============================================================
c1, c2, c3 = st.columns(3)
c1.metric("Availability (Unplanned only)", f"{A_unplanned*100:.2f} %")
c2.metric("Availability Total", f"{A_total*100:.2f} %")
downtime_unplanned = (1 - A_unplanned) * 8760
downtime_total = (1 - A_total) * 8760
c3.metric("Downtime Total", f"{downtime_total:.0f} jam/tahun")

st.caption(f"Unplanned downtime: {downtime_unplanned:.1f} jam/thn · "
           f"Planned downtime: {planned_outage_hari*24:.0f} jam/thn · "
           f"β = {common_cause_beta}")

# Grafik ranking availability per komponen
st.subheader("📊 Ranking Komponen (paling critical di bawah)")
df_rank = df_hasil.sort_values("Availability")
fig, ax = plt.subplots(figsize=(10, max(4, len(df_rank) * 0.35)))
ax.barh(df_rank["Nama"], df_rank["Availability"] * 100, color="#3b82f6")
ax.set_xlabel("Availability (%)")
ax.axvline(df_rank["Availability"].min() * 100, color="red", linestyle="--", alpha=0.5)
plt.tight_layout()
st.pyplot(fig)

# Tabel grup
st.subheader("📋 Availability per Grup")
df_grup_show = pd.DataFrame([
    {"Grup": g, "Tipe": df_grup[df_grup["Grup"] == g]["Tipe"].values[0],
     "Availability (%)": f"{grup_avail[g]*100:.4f}"}
    for g in urutan_sistem
])
st.dataframe(df_grup_show, use_container_width=True, hide_index=True)

# Kurva R(t)
st.subheader("📈 Kurva Reliability R(t) Sistem")
def R_sistem(t_jam):
    R_g = {}
    for _, g in df_grup.iterrows():
        nama, tipe, k, n = g["Grup"], g["Tipe"], int(g["k"]), int(g["n"])
        sub = df_hasil[df_hasil["Grup"] == nama]
        R_ind = np.exp(-(sub["Lambda/yr"] / 8760) * t_jam).values
        if tipe == "Series":
            R_g[nama] = float(np.prod(R_ind)) if len(R_ind) else 1.0
        elif tipe == "Parallel":
            R_g[nama] = float(1 - np.prod(1 - R_ind))
        elif tipe == "kooN":
            R_pad = np.ones(n) * (R_ind[0] if len(R_ind) else 1.0)
            R_pad[:len(R_ind)] = R_ind
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
ax2.set_title("Probabilitas tidak ada kegagalan sama sekali sampai waktu t")
ax2.grid(alpha=0.3)
plt.tight_layout()
st.pyplot(fig2)
st.caption("⚠️ R(t) berbeda dari Availability. R(t) = probabilitas 'tidak pernah gagal' "
           "(tanpa repair). Availability = fraksi waktu plant bisa beroperasi (dengan repair).")

# Download CSV
st.subheader("⬇️ Download Hasil")
csv = df_hasil.to_csv(index=False)
st.download_button("Download tabel komponen (CSV)", csv,
                   file_name="rbd_hasil.csv", mime="text/csv")
