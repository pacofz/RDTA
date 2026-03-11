import streamlit as st
import pandas as pd
import re
import plotly.express as px
from datetime import datetime
import math
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CHATSTAT PRO", page_icon="📄", layout="centered")

# --- MOTOR DE PROCESAMIENTO ---
def parse_chat(file_content):
    content = file_content.decode("utf-8")
    lines = content.split('\n')
    data = []
    # Regex mejorado para soportar múltiples formatos de fecha y hora
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

            # Análisis de Matagrupos (Silencio > 6hs)
            is_matagrupos = False
            if prev_timestamp and (ts - prev_timestamp).total_seconds() / 3600 > 6:
                if len(data) > 0: data[-1]['is_matagrupos'] = True

            data.append({
                'timestamp': ts, 
                'hour': ts.hour,
                'day_name': ts.strftime('%A'),
                'sender': sender,
                'message': message, 
                'msg_len': len(message), 
                'is_matagrupos': False,
                'is_noctambulo': 0 <= ts.hour <= 5,
                'has_audio': any(x in message.lower() for x in ['audio', 'ptt', 'nota de voz', '0:']),
                'is_question': '?' in message,
                'is_toxic': bool(re.search(r'boludo|pelotudo|forro|hdp|mierda|paja', message.lower()))
            })
            prev_timestamp = ts
            
    return pd.DataFrame(data)

# --- GENERADOR DE PDF VECTORIAL ---
class ChatReportPDF(FPDF):
    def header(self):
        self.set_fill_color(10, 10, 10)
        self.rect(0, 0, 210, 297, 'F')
        self.set_font('helvetica', 'B', 8)
        self.set_text_color(60, 60, 60)
        self.cell(0, 10, 'CHATSTAT INTELLIGENCE - VECTOR ENGINE v2.5', 0, 1, 'C')

    def draw_vector_chart(self, labels, values, title, desc):
        if not labels or not values: return
        self.add_page()
        self.ln(10)
        self.set_font('helvetica', 'B', 18)
        self.set_text_color(16, 185, 129)
        self.cell(0, 10, title.upper(), 0, 1, 'L')
        self.ln(2)
        self.set_font('helvetica', '', 10)
        self.set_text_color(200, 200, 200)
        self.multi_cell(0, 5, desc)
        self.ln(10)

        # Configuración de barras
        max_val = max(values) if max(values) > 0 else 1
        chart_w = 120
        start_x = 60
        row_h = 8

        for label, val in zip(labels[:15], values[:15]): # Top 15
            self.set_font('helvetica', '', 9)
            self.set_text_color(150, 150, 150)
            self.set_x(10)
            self.cell(start_x - 15, row_h, str(label)[:22], 0, 0, 'R')
            
            # Dibujo de barra (Vector)
            bar_w = (val / max_val) * chart_w
            self.set_fill_color(16, 185, 129)
            self.rect(start_x, self.get_y() + 1.5, bar_w, row_h - 3, 'F')
            
            self.set_x(start_x + bar_w + 2)
            self.set_text_color(255, 255, 255)
            self.cell(20, row_h, f"{val:,.0f}", 0, 1, 'L')
            self.ln(1)

def create_pdf_report(df):
    pdf = ChatReportPDF()
    
    # Portada
    pdf.add_page()
    pdf.ln(80)
    pdf.set_font('helvetica', 'B', 40)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(0, 20, 'RADIOGRAFÍA DIGITAL', 0, 1, 'C')
    pdf.set_font('helvetica', '', 15)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, f'Análisis de {len(df):,} mensajes', 0, 1, 'C')

    # 1. Mensajes Totales
    counts = df['sender'].value_counts().reset_index()
    pdf.draw_vector_chart(counts['sender'].tolist(), counts['count'].tolist(), 
                         "Ranking de Actividad", "Quién domina la conversación por volumen de mensajes.")

    # 2. El Club Noctámbulo (Corregido)
    noct = df[df['is_noctambulo']]['sender'].value_counts().reset_index()
    pdf.draw_vector_chart(noct['sender'].tolist(), noct['count'].tolist(), 
                         "Club Noctámbulo", "Mensajes enviados entre las 00:00 y las 05:59. Los que no duermen.")

    # 3. El Matagrupos
    mata = df[df['is_matagrupos']]['sender'].value_counts().reset_index()
    pdf.draw_vector_chart(mata['sender'].tolist(), mata['count'].tolist(), 
                         "El Matagrupos", "Quién envía el último mensaje antes de un silencio de más de 6 horas.")

    # 4. Toxicidad Amistosa (NUEVO)
    toxic = df[df['is_toxic']]['sender'].value_counts().reset_index()
    pdf.draw_vector_chart(toxic['sender'].tolist(), toxic['count'].tolist(), 
                         "Índice de Confianza", "Frecuencia de insultos amistosos y modismos detectados.")

    # 5. El Fantasma (NUEVO - Quien menos habla)
    ghost = df['sender'].value_counts().sort_values(ascending=True).reset_index()
    pdf.draw_vector_chart(ghost['sender'].tolist(), ghost['count'].tolist(), 
                         "El Fantasma", "Integrantes que observan desde las sombras (menor actividad).")

    return bytes(pdf.output())

# --- UI ---
st.markdown('<h1 class="hero-title">CHAT<span class="emerald-text">STAT</span> PRO</h1>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Carga tu chat de WhatsApp (.txt)", type=["txt"])

if uploaded_file:
    df = parse_chat(uploaded_file.getvalue())
    if not df.empty:
        st.success(f"Procesados {len(df)} mensajes con éxito.")
        pdf_bytes = create_pdf_report(df)
        st.download_button("⬇️ DESCARGAR REPORTE PDF", data=pdf_bytes, 
                         file_name="Reporte_ChatStat.pdf", mime="application/pdf")













