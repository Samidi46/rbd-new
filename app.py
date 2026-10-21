st.divider()
st.subheader("📌 Pilih Sistem untuk Analisis Detail")

# Buat 3 kolom agar tombolnya rapi
col1, col2, col3 = st.columns(3)

# Di Streamlit, kita bisa menggunakan loop agar tidak menulis 23 baris st.page_link
# Tapi untuk tampilan yang lebih rapi, kita bagi berdasarkan kolom.

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
