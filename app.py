# ... (Mantener las importaciones y la clase ChatReportPDF igual)

# --- ESTILOS CSS ACTUALIZADOS ---
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #f4f4f5; }
    
    .hero-title {
        font-size: 80px !important; 
        line-height: 0.8 !important; 
        margin-bottom: 10px !important;
        text-align: center !important; 
        font-weight: 900 !important; 
        text-transform: uppercase !important; 
        font-style: italic !important;
        letter-spacing: -2px !important;
    }
    
    .emerald-text { 
        color: #10b981 !important; 
        font-style: normal !important;
        display: block;
        font-size: 50px !important;
    }

    .step-container {
        background-color: #111;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #10b981;
        margin-bottom: 20px;
    }

    .stat-card {
        background-color: #1a1a1a;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #333;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    # 1. TITULO IMPACTANTE
    st.markdown('<p class="hero-title">RADIOGRAFÍA <br><span class="emerald-text">DE TU AMISTAD.</span></p>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Auditoría algorítmica de vínculos digitales.</p>", unsafe_allow_html=True)
    
    st.write("---")

    # 2. PASO A PASO RESUMIDO
    st.markdown("### ⚡ EXPORTA EN 10 SEGUNDOS")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="step-container"><b>1. Entra</b><br>Al chat de WhatsApp</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="step-container"><b>2. Ajustes</b><br>Click en "Más" o en el nombre</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="step-container"><b>3. Exportar</b><br>Elegir "Exportar chat"</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="step-container"><b>4. Sin Archivos</b><br>Seleccionar "Sin archivos"</div>', unsafe_allow_html=True)

    st.write("")

    # 3. CARGADOR DE ARCHIVOS
    st.markdown("### 📂 CARGA TU ARCHIVO .TXT")
    uploaded_file = st.file_uploader("", type=["txt"])
    
    if uploaded_file:
        df = parse_chat(uploaded_file.getvalue())
        if not df.empty:
            st.success(f"✅ {len(df):,} mensajes procesados.")
            pdf_bytes = create_pdf_report(df)
            
            st.download_button(
                label="⬇️ DESCARGAR REPORTE ESTRATÉGICO PDF",
                data=pdf_bytes,
                file_name=f"Analisis_ChatStat_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error("Error: Formato no compatible.")

    st.write("---")

    # 4. EJEMPLOS DE ESTADÍSTICAS (PREVIEW)
    st.markdown("### 📊 ¿QUÉ REVELA EL INFORME?")
    
    ex1, ex2, ex3 = st.columns(3)
    with ex1:
        st.markdown("""
        <div class="stat-card">
            <h4 style='margin:0; color:#10b981;'>VELOCIDAD</h4>
            <p style='font-size:12px; color:#888;'>¿Quién clava el visto por más de 4 horas?</p>
        </div>
        """, unsafe_allow_html=True)
    with ex2:
        st.markdown("""
        <div class="stat-card">
            <h4 style='margin:0; color:#10b981;'>INSOMNIO</h4>
            <p style='font-size:12px; color:#888;'>Ranking de actividad entre las 00 y las 06 AM.</p>
        </div>
        """, unsafe_allow_html=True)
    with ex3:
        st.markdown("""
        <div class="stat-card">
            <h4 style='margin:0; color:#10b981;'>TOXICIDAD</h4>
            <p style='font-size:12px; color:#888;'>Filtro de "palabras calientes" y puteadas.</p>
        </div>
        """, unsafe_allow_html=True)

    # Preview Visual de un "Chat" analizado
    st.write("")
    with st.expander("👀 Ver ejemplo de visualización"):
        st.image("https://raw.githubusercontent.com/andfanilo/social-media-tutorials/master/streamlit-charts/header.png", caption="Ejemplo de métricas de frecuencia horaria")
        st.info("El reporte PDF final utiliza gráficos vectoriales de alta definición (Formato Arquitectura).")

if __name__ == "__main__":
    main()








