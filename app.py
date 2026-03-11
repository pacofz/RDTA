import streamlit as st
import pandas as pd
import re
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CHATSTAT PRO", page_icon="📄", layout="centered")

# --- ESTILOS CSS CORREGIDOS ---
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #f4f4f5; }
    
    /* Titulo XL para la web */
    .hero-title {
        font-size: 100px !important; 
        line-height: 0.8 !important; 
        margin-bottom: 30px !important;
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
        font-size: 60px !important;
    }
    
    /* Ajuste para el cargador de archivos */
    .stFileUploader { padding-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE PROCESAMIENTO ---
def parse_chat(file_content):
    content = file_content.decode("utf-8")
    lines = content.split('\n')
    data = []
    line_regex = r'^\[?(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4}),?\s(\d{1,2}:\d{2}(?::\d{2})?)\s?(?:a\.\s?m\.|p\.\s?m\.|AM|PM|am|pm)?\]?\s?(?:-\s|:\s)?([^:]+):\s(.*)'
    
    prev_timestamp = None
    for line in lines:
        match = re.match(line_regex, line)
        if match:
            date_str, time_str, sender, message = match.groups()
            sender = sender.strip().replace('[', '').replace(']', '')
            try:
                clean_date = date_str.replace('.', '/').replace('-', '/')
                date_parts = clean_date.split('/')
                if len(date_parts[2]) == 2: clean_date = f"{date_parts[0]}/{date_parts[1]}/20{date_parts[2]}"
                ts = datetime.strptime(f"{clean_date} {time_str[:5]}", "%d/%m/%Y %H:%M")
            except: continue

            is_matagrupos = False
            if prev_timestamp and (ts - prev_timestamp).total_seconds() / 3600 > 6:
                if len(data) > 0: data[-1]['is_matagrupos'] = True

            data.append({
                'timestamp': ts, 
                'hour': ts.hour,
                'sender': sender,
                'message': message, 
                'is_matagrupos': False,
                'is_noctambulo': 0 <= ts.hour <= 5,
                'is_toxic': bool(re.search(r'boludo|pelotudo|forro|hdp|mierda|paja', message.lower()))
            })
            prev_timestamp = ts
    return pd.DataFrame(data)

# --- GENERADOR DE PDF HORIZONTAL ---
class ChatReportPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        
    def header(self):
        self.set_fill_color(5, 5, 5)
        self.rect(0, 0, 297, 210, 'F')
        if self.page_no() > 1:
            self.set_font('helvetica', 'B', 8)
            self.set_text_color(50, 50, 50)
            self.cell(0, 10, 'CHATSTAT INTELLIGENCE REPORT - PRO VERSION', 0, 1, 'R')

    def draw_vector_chart(self, labels, values, title, desc):
        if not labels or not values: return
        self.add_page()
        self.ln(10)
        self.set_font('helvetica', 'BI', 24)
        self.set_text_color(16, 185, 129)
        self.cell(0, 15, title.upper(), 0, 1, 'L')
        
        self.set_font('helvetica', '', 11)
        self.set_text_color(180, 180, 180)
        self.multi_cell(0, 6, desc)
        self.ln(15)

        max_val = max(values) if max(values) > 0 else 1
        chart_max_w = 180 
        start_x = 80
        row_h = 9

        for label, val in zip(labels[:12], values[:12]):
            self.set_font('helvetica', 'B', 10)
            self.set_text_color(140, 140, 140)
            self.set_x(10)
            self.cell(start_x - 15, row_h, str(label)[:30], 0, 0, 'R')
            
            bar_w = (val / max_val) * chart_max_w
            self.set_fill_color(16, 185, 129)
            self.rect(start_x, self.get_y() + 1, bar_w, row_h - 2, 'F')
            
            self.set_x(start_x + bar_w + 3)
            self.set_text_color(255, 255, 255)
            self.cell(20, row_h, f"{val:,.0f}", 0, 1, 'L')
            self.ln(2)

def create_pdf_report(df):
    pdf = ChatReportPDF()
    
    # PORTADA PDF (Idéntica a la nueva Web)
    pdf.add_page()
    pdf.ln(50)
    pdf.set_font('helvetica', 'BI', 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 35, 'RADIOGRAFÍA', 0, 1, 'C')
    
    pdf.set_font('helvetica', 'B', 45)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(0, 25, 'DE TU AMISTAD.', 0, 1, 'C')
    
    pdf.ln(20)
    pdf.set_font('helvetica', '', 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, f"ESTUDIO BASADO EN {len(df):,} MENSAJES", 0, 1, 'C')

    # Métricas
    counts = df['sender'].value_counts().reset_index()
    pdf.draw_vector_chart(counts['sender'].tolist(), counts['count'].tolist(), "Ranking de Actividad", "Volumen total de mensajes por integrante.")

    noct = df[df['is_noctambulo']]['sender'].value_counts().reset_index()
    pdf.draw_vector_chart(noct['sender'].tolist(), noct['count'].tolist(), "Club Noctámbulo", "Actividad entre 00:00 y 05:59 hs.")

    return bytes(pdf.output())

# --- INTERFAZ STREAMLIT ---
def main():
    # El título ahora tiene el tamaño XL que pediste
    st.markdown('<p class="hero-title">RADIOGRAFÍA <br><span class="emerald-text">DE TU AMISTAD.</span></p>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("", type=["txt"])
    
    if uploaded_file:
        df = parse_chat(uploaded_file.getvalue())
        if not df.empty:
            st.success(f"Análisis completo: {len(df)} registros.")
            pdf_bytes = create_pdf_report(df)
            st.download_button(
                label="⬇️ DESCARGAR REPORTE FINAL",
                data=pdf_bytes,
                file_name=f"Radiografia_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()















