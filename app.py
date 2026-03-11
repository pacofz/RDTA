import streamlit as st
import pandas as pd
import re
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CHATSTAT PRO", page_icon="📄", layout="centered")

# --- ESTILOS CSS (Estética XL e Impactante) ---
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #f4f4f5; }
    
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
    
    .stFileUploader { padding-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE PROCESAMIENTO CON FILTROS ANTI-SISTEMA ---
def parse_chat(file_content):
    content = file_content.decode("utf-8")
    lines = content.split('\n')
    data = []
    
    # Regex robusto para capturar fecha, hora, emisor y mensaje
    line_regex = r'^\[?(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4}),?\s(\d{1,2}:\d{2}(?::\d{2})?)\s?(?:a\.\s?m\.|p\.\s?m\.|AM|PM|am|pm)?\]?\s?(?:-\s|:\s)?([^:]+):\s(.*)'
    
    # Palabras clave para ignorar mensajes automáticos de WhatsApp
    system_keywords = ['creó este grupo', 'cambió el asunto', 'añadió a', 'salió', 'eliminó a', 'cambió la descripción', 'cambió el ícono']
    
    prev_timestamp = None
    prev_sender = None
    
    for line in lines:
        match = re.match(line_regex, line)
        if match:
            date_str, time_str, sender, message = match.groups()
            
            # Limpieza del emisor
            sender = sender.strip().replace('[', '').replace(']', '')
            sender = re.sub(r'\u202a|\u202c|\xa0', '', sender).strip()
            
            # FILTROS: Evita que el nombre del grupo o mensajes de sistema entren como usuarios
            if len(sender) > 35: continue
            if any(key in sender.lower() for key in system_keywords): continue
            
            try:
                clean_date = date_str.replace('.', '/').replace('-', '/')
                date_parts = clean_date.split('/')
                if len(date_parts[2]) == 2: clean_date = f"{date_parts[0]}/{date_parts[1]}/20{date_parts[2]}"
                ts = datetime.strptime(f"{clean_date} {time_str[:5]}", "%d/%m/%Y %H:%M")
            except: continue

            # Métrica de Tiempo de Respuesta (en minutos)
            response_time = None
            if prev_timestamp and prev_sender and sender != prev_sender:
                diff = (ts - prev_timestamp).total_seconds() / 60
                if diff < 720: # Límite de 12hs para considerar que es una respuesta directa
                    response_time = diff

            data.append({
                'timestamp': ts, 
                'hour': ts.hour,
                'sender': sender,
                'message': message, 
                'response_time_min': response_time,
                'is_noctambulo': 0 <= ts.hour <= 5,
                'is_toxic': bool(re.search(r'boludo|pelotudo|forro|hdp|mierda|paja', message.lower()))
            })
            prev_timestamp, prev_sender = ts, sender
            
    return pd.DataFrame(data)

# --- GENERADOR DE PDF (FORMATO LANDSCAPE VECTORIAL) ---
class ChatReportPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        
    def header(self):
        self.set_fill_color(5, 5, 5) # Fondo negro profundo
        self.rect(0, 0, 297, 210, 'F')
        if self.page_no() > 1:
            self.set_font('helvetica', 'B', 8)
            self.set_text_color(50, 50, 50)
            self.cell(0, 10, 'CHATSTAT INTELLIGENCE REPORT - PRO VERSION', 0, 1, 'R')

    def draw_vector_chart(self, labels, values, title, desc, suffix=""):
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

        # Configuración de barras vectoriales
        max_val = max(values) if max(values) > 0 else 1
        chart_max_w = 180 
        start_x = 80
        row_h = 9

        for label, val in zip(labels[:12], values[:12]):
            self.set_font('helvetica', 'B', 10)
            self.set_text_color(140, 140, 140)
            self.set_x(10)
            self.cell(start_x - 15, row_h, str(label)[:30], 0, 0, 'R')
            
            # Dibujo de barra (Instrucción vectorial directa)
            bar_w = (val / max_val) * chart_max_w
            self.set_fill_color(16, 185, 129)
            self.rect(start_x, self.get_y() + 1, bar_w, row_h - 2, 'F')
            
            # Etiqueta de valor
            self.set_x(start_x + bar_w + 3)
            self.set_text_color(255, 255, 255)
            self.cell(40, row_h, f"{val:,.1f} {suffix}", 0, 1, 'L')
            self.ln(2)

def create_pdf_report(df):
    pdf = ChatReportPDF()
    
    # PORTADA PDF (Impacto Visual XL)
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
    pdf.cell(0, 10, f"AUDITORÍA DIGITAL SOBRE {len(df):,} REGISTROS", 0, 1, 'C')

    # --- MÉTRICAS ---
    
    # 1. Velocidad de Reacción
    resp_df = df.dropna(subset=['response_time_min'])
    if not resp_df.empty:
        avg_resp = resp_df.groupby('sender')['response_time_min'].mean().sort_values(ascending=False).reset_index()
        pdf.draw_vector_chart(avg_resp['sender'].tolist(), avg_resp['response_time_min'].tolist(), 
                             "Velocidad de Reacción", 
                             "Tiempo promedio en minutos que cada integrante tarda en contestar mensajes. Las barras más largas indican mayor demora.",
                             suffix="min")

    # 2. Ranking de Actividad
    counts = df['sender'].value_counts().reset_index()
    pdf.draw_vector_chart(counts['sender'].tolist(), counts['count'].tolist(), 
                         "Ranking de Actividad", "Volumen total de participación operativa en el chat.")

    # 3. Noctámbulos
    noct = df[df['is_noctambulo']]['sender'].value_counts().reset_index()
    if not noct.empty:
        pdf.draw_vector_chart(noct['sender'].tolist(), noct['count'].tolist(), 
                             "Operatividad Nocturna", "Cantidad de mensajes registrados entre las 00:00 y las 05:59 hs.")

    return bytes(pdf.output())

# --- INTERFAZ STREAMLIT ---
def main():
    st.markdown('<p class="hero-title">RADIOGRAFÍA <br><span class="emerald-text">DE TU AMISTAD.</span></p>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("", type=["txt"])
    
    if uploaded_file:
        df = parse_chat(uploaded_file.getvalue())
        if not df.empty:
            st.success(f"Análisis exitoso de {len(df)} mensajes.")
            
            pdf_bytes = create_pdf_report(df)
            
            st.download_button(
                label="⬇️ DESCARGAR REPORTE ESTRATÉGICO PDF",
                data=pdf_bytes,
                file_name=f"Analisis_ChatStat_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
        else:
            st.error("El formato del chat no es compatible o está vacío.")

if __name__ == "__main__":
    main()
















