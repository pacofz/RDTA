import streamlit as st
import pandas as pd
import re
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CHATSTAT PRO", page_icon="📄", layout="centered")

# --- ESTILOS CSS (Estética de la Web) ---
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #f4f4f5; }
    .hero-title {
        font-size: 70px; line-height: 0.9; margin-bottom: 20px;
        text-align: center; font-weight: 900; text-transform: uppercase; font-style: italic;
    }
    .emerald-text { color: #10b981; font-style: normal; }
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

# --- GENERADOR DE PDF HORIZONTAL Y ESTÉTICO ---
class ChatReportPDF(FPDF):
    def __init__(self):
        # Orientación Landscape (Horizontal)
        super().__init__(orientation='L', unit='mm', format='A4')
        
    def header(self):
        # Fondo oscuro en todo el reporte
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
        # Título estilo Web (Esmeralda e Itálico)
        self.set_font('helvetica', 'BI', 24)
        self.set_text_color(16, 185, 129)
        self.cell(0, 15, title.upper(), 0, 1, 'L')
        
        # Descripción
        self.set_font('helvetica', '', 11)
        self.set_text_color(180, 180, 180)
        self.multi_cell(0, 6, desc)
        self.ln(15)

        # Configuración de barras para formato horizontal
        max_val = max(values) if max(values) > 0 else 1
        chart_max_w = 180 # Más ancho por ser horizontal
        start_x = 80
        row_h = 9

        for label, val in zip(labels[:12], values[:12]):
            self.set_font('helvetica', 'B', 10)
            self.set_text_color(140, 140, 140)
            self.set_x(10)
            self.cell(start_x - 15, row_h, str(label)[:30], 0, 0, 'R')
            
            # Dibujo de barra (Instrucción vectorial rápida)
            bar_w = (val / max_val) * chart_max_w
            self.set_fill_color(16, 185, 129)
            self.rect(start_x, self.get_y() + 1, bar_w, row_h - 2, 'F')
            
            # Valor numérico
            self.set_x(start_x + bar_w + 3)
            self.set_text_color(255, 255, 255)
            self.cell(20, row_h, f"{val:,.0f}", 0, 1, 'L')
            self.ln(2)

def create_pdf_report(df):
    pdf = ChatReportPDF()
    
    # PORTADA (Estética idéntica a la Web)
    pdf.add_page()
    pdf.ln(50)
    
    # Texto RADIOGRAFÍA (Doble de grande: 80)
    pdf.set_font('helvetica', 'BI', 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 35, 'RADIOGRAFÍA', 0, 1, 'C')
    
    # Texto DE TU AMISTAD (En Esmeralda)
    pdf.set_font('helvetica', 'B', 45)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(0, 25, 'DE TU AMISTAD.', 0, 1, 'C')
    
    pdf.ln(20)
    pdf.set_font('helvetica', '', 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, f"ANÁLISIS DE DATOS BASADO EN {len(df):,} REGISTROS", 0, 1, 'C')
    pdf.cell(0, 10, f"GENERADO EL {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'C')

    # --- MÉTRICAS ---
    # 1. Ranking General
    counts = df['sender'].value_counts().reset_index()
    pdf.draw_vector_chart(counts['sender'].tolist(), counts['count'].tolist(), 
                         "Ranking de Actividad", "Análisis volumétrico de mensajes por cada integrante del grupo.")

    # 2. Los Noctámbulos
    noct = df[df['is_noctambulo']]['sender'].value_counts().reset_index()
    pdf.draw_vector_chart(noct['sender'].tolist(), noct['count'].tolist(), 
                         "Club de los Noctámbulos", "Frecuencia de mensajes enviados en la franja de 00:00 a 05:59 hs.")

    # 3. Toxicidad (Boludeo)
    toxic = df[df['is_toxic']]['sender'].value_counts().reset_index()
    pdf.draw_vector_chart(toxic['sender'].tolist(), toxic['count'].tolist(), 
                         "Índice de Confianza", "Métrica basada en el uso de términos coloquiales e insultos amistosos detectados.")

    # 4. El Fantasma
    ghost = df['sender'].value_counts().sort_values(ascending=True).reset_index()
    pdf.draw_vector_chart(ghost['sender'].tolist(), ghost['count'].tolist(), 
                         "Ranking del Silencio", "Identificación de los usuarios con menor tasa de respuesta en el periodo.")

    return bytes(pdf.output())

# --- INTERFAZ STREAMLIT ---
def main():
    st.markdown('<p class="hero-title">RADIOGRAFÍA DE <br><span class="emerald-text">TU AMISTAD.</span></p>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("", type=["txt"])
    
    if uploaded_file:
        df = parse_chat(uploaded_file.getvalue())
        if not df.empty:
            st.success(f"Sistema listo. {len(df)} mensajes detectados.")
            
            pdf_bytes = create_pdf_report(df)
            
            st.download_button(
                label="⬇️ DESCARGAR REPORTE PDF HORIZONTAL",
                data=pdf_bytes,
                file_name=f"ChatStat_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()














