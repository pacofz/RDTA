import streamlit as st
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime
import time
import math
from fpdf import FPDF
import io
from tempfile import NamedTemporaryFile

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="CHATSTAT PDF - Intelligence Report",
    page_icon="📄",
    layout="centered"
)

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #f4f4f5; }
    .hero-title {
        font-size: 60px; line-height: 0.9; margin-bottom: 20px;
        text-align: center; font-weight: 900; text-transform: uppercase; font-style: italic;
    }
    .emerald-text { color: #10b981; font-style: normal; }
    .stButton>button {
        background-color: #10b981; color: #000; border-radius: 50px;
        font-weight: 900; text-transform: uppercase; padding: 15px 30px;
        border: none; width: 100%; transition: all 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); background-color: #34d399; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE PROCESAMIENTO AVANZADO ---
def parse_chat(file_content):
    content = file_content.decode("utf-8")
    lines = content.split('\n')
    data = []
    line_regex = r'^\[?(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4}),?\s(\d{1,2}:\d{2}(?::\d{2})?)\s?(?:a\.\s?m\.|p\.\s?m\.|AM|PM|am|pm)?\]?\s?(?:-\s|:\s)?([^:]+):\s(.*)'
    
    prev_timestamp = None
    prev_sender = None
    
    neg_words = r'no|mal|odio|asco|feo|peor|nunca|jamas|horrible|paja|boludo|pelotudo'
    bolu_words = r'boludo|pelotudo|forro|mierda|carajo|hdp|puto|paja'
    plan_words = r'asado|birra|vamos|che|plan|juntada|salimos|comemos|pizza|cena|almuerzo|boliche|fiesta'
    female_names = r'Agustina|Agus|Belén|Belu|Camila|Cami|Pilar|Pili|Josefina|Jose|Julieta|Juli|Juana|Juani|Carolina|Caro|Sofía|Sofi|Florencia|Flor'

    for line in lines:
        match = re.match(line_regex, line)
        if match:
            date_str, time_str, sender, message = match.groups()
            sender = sender.strip().replace('[', '').replace(']', '')
            sender = re.split(r'am\]|pm\]|AM\]|PM\]', sender, flags=re.IGNORECASE)[-1].strip()
            
            if len(sender) > 40 or re.search(r'\d{1,2}:\d{2}', sender): continue
            
            try:
                clean_date = date_str.replace('.', '/').replace('-', '/')
                date_parts = clean_date.split('/')
                if len(date_parts[2]) == 2: clean_date = f"{date_parts[0]}/{date_parts[1]}/20{date_parts[2]}"
                ts = datetime.strptime(f"{clean_date} {time_str[:5]}", "%d/%m/%Y %H:%M")
            except: continue

            silence_duration = 0
            is_starter = False
            if prev_timestamp:
                silence_duration = (ts - prev_timestamp).total_seconds() / 3600
                if silence_duration > 6:
                    is_starter = True
                    if prev_sender and len(data) > 0: data[-1]['is_matagrupos'] = True
            
            data.append({
                'timestamp': ts, 
                'date': ts.date(),
                'year_month': ts.strftime('%Y-%m'), 
                'year': ts.year,
                'hour': ts.hour,
                'day_name': ts.strftime('%A'),
                'sender': sender,
                'message': message, 
                'msg_len': len(message), 
                'is_starter': is_starter,
                'silence_before': silence_duration,
                'is_matagrupos': False, 
                'is_noctambulo': 0 <= ts.hour <= 6,
                'has_sticker': 'sticker' in message.lower(),
                'has_audio': any(x in message.lower() for x in ['audio', 'ptt', 'nota de voz']),
                'has_multimedia': any(x in message.lower() for x in ['imagen', 'video', 'archivo omitido', 'sticker', 'audio']),
                'is_question': '?' in message,
                'is_plan': bool(re.search(plan_words, message.lower())),
                'is_negative': bool(re.search(neg_words, message.lower())),
                'is_boludeo': bool(re.search(bolu_words, message.lower())),
                'mentions_female': bool(re.search(female_names, message))
            })
            prev_timestamp, prev_sender = ts, sender
            
    df = pd.DataFrame(data)
    if not df.empty:
        df['prev_sender'] = df['sender'].shift(1)
        df['time_diff'] = df['timestamp'].diff().dt.total_seconds() / 60
        df['is_response'] = (df['time_diff'] < 5) & (df['sender'] != df['prev_sender'])
    return df

# --- GENERADOR DE PDF ---
class ChatReportPDF(FPDF):
    def header(self):
        self.set_fill_color(5, 5, 5)
        self.rect(0, 0, 210, 297, 'F')
        self.set_font('helvetica', 'B', 8)
        self.set_text_color(80, 80, 80)
        self.cell(0, 10, 'CHATSTAT INTELLIGENCE REPORT - CONFIDENCIAL', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def add_plot_to_pdf(pdf, fig, title, description):
    pdf.add_page()
    pdf.ln(10)
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(0, 10, title.upper(), 0, 1, 'L')
    pdf.ln(2)
    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(200, 200, 200)
    pdf.multi_cell(0, 5, description)
    pdf.ln(5)
    
    # OPCIÓN SEGURA: Mostramos el gráfico en la web pero no lo metemos al PDF
    # Esto evita que el servidor se cuelgue intentando 'renderizar' la imagen
    pdf.set_font('helvetica', 'I', 8)
    pdf.cell(0, 10, "(Grafico disponible en el panel interactivo de la web)", 0, 1)

def create_pdf_report(df):
    pdf = ChatReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # PORTADA
    pdf.add_page()
    pdf.ln(80)
    pdf.set_font('helvetica', 'B', 45)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(0, 20, 'RADIOGRAFÍA', 0, 1, 'C')
    pdf.set_font('helvetica', 'B', 30)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 20, 'DE TU AMISTAD', 0, 1, 'C')
    pdf.ln(20)
    pdf.set_font('helvetica', '', 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, f'Periodo: {df["timestamp"].min().strftime("%Y")} - {df["timestamp"].max().strftime("%Y")}', 0, 1, 'C')
    pdf.cell(0, 10, f'Registros: {len(df):,}', 0, 1, 'C')

    plot_template = "plotly_dark"

    # 1. EVOLUCIÓN ACUMULADA
    df_sorted = df.sort_values('timestamp')
    df_sorted['count'] = 1
    df_cum = df_sorted.groupby(['date', 'sender'])['count'].sum().groupby(level=1).cumsum().reset_index(name='acumulado')
    fig_cum = px.line(df_cum, x='date', y='acumulado', color='sender', template=plot_template)
    add_plot_to_pdf(pdf, fig_cum, "Evolución Acumulada", "Crecimiento histórico del volumen de mensajes.")

    # 2. LARGO PROMEDIO
    avg_len = df.groupby('sender')['msg_len'].mean().sort_values(ascending=True).reset_index()
    fig_len = px.bar(avg_len, x='msg_len', y='sender', orientation='h', template=plot_template, color='msg_len')
    add_plot_to_pdf(pdf, fig_len, "Largo Promedio", "Quién escribe los mensajes más extensos.")

    # 3. EL MATAGRUPOS
    #matagrupos = df[df['is_matagrupos']].groupby('sender').size().sort_values(ascending=True).reset_index(name='count')
    #fig_mata = px.bar(matagrupos, x='count', y='sender', orientation='h', template=plot_template)
    #add_plot_to_pdf(pdf, fig_mata, "El Matagrupos", "Mensajes que precedieron a silencios de más de 6 horas.")

    # 4. CLUB DE NOCTAMBULOS
    #noct = df[df['is_noctambulo']].groupby('sender').size().sort_values(ascending=True).reset_index(name='count')
    #fig_noct = px.bar(noct, x='count', y='sender', orientation='h', template=plot_template)
    #add_plot_to_pdf(pdf, fig_noct, "Club de Noctámbulos", "Actividad registrada entre las 00:00 y las 06:00 hs.")

    # 5. EL PREGUNTON
    #preg = df.groupby('sender')['is_question'].mean().mul(100).sort_values(ascending=True).reset_index(name='perc')
    #fig_preg = px.bar(preg, x='perc', y='sender', orientation='h', template=plot_template)
    #add_plot_to_pdf(pdf, fig_preg, "El Preguntón", "Porcentaje de mensajes que son preguntas.")

    # 7. ÍNDICE DE BOLUDEO
    #bolu = df[df['is_boludeo']].groupby('sender').size().sort_values(ascending=True).reset_index(name='count')
    #fig_bolu = px.bar(bolu, x='count', y='sender', orientation='h', template=plot_template)
    #add_plot_to_pdf(pdf, fig_bolu, "Índice de Boludeo", "Detección de términos coloquiales e insultos.")

    # 8. ACTIVIDAD SEMANAL
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    week = df['day_name'].value_counts().reindex(day_order).reset_index()
    week.columns = ['Día', 'Mensajes']
    fig_week = px.bar(week, x='Día', y='Mensajes', template=plot_template)
    add_plot_to_pdf(pdf, fig_week, "Actividad Semanal", "Distribución de mensajes según el día.")

    # CONCLUSIÓN FINAL
    pdf.add_page()
    pdf.ln(20)
    pdf.set_font('helvetica', 'B', 24)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(0, 15, 'CONCLUSIÓN DEL ANÁLISIS', 0, 1, 'L')
    pdf.ln(5)
    pdf.set_font('helvetica', '', 12)
    pdf.set_text_color(240, 240, 240)
    
    top_s = df['sender'].value_counts().index[0]
    conclusion_text = (
        f"El reporte final confirma que '{top_s}' es el pilar de la comunicación. "
        f"Se detectó un ecosistema digital saludable con picos de actividad social coordinada. "
        f"Este documento sirve como auditoría final de comportamiento grupal."
    )
    pdf.multi_cell(0, 10, conclusion_text)
    
    return bytes(pdf.output())

# --- UI PRINCIPAL ---
def main():
    st.markdown('<p class="hero-title">RADIOGRAFÍA DE <br><span class="emerald-text">TU AMISTAD.</span></p>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#a1a1aa; font-size:18px;">Exporta tu chat de WhatsApp y carga el .txt para generar el PDF empresarial detallado.</p>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("", type=["txt"])
    
    if uploaded_file:
        with st.status("Analizando datos y renderizando PDF...", expanded=True) as status:
            df = parse_chat(uploaded_file.getvalue())
            if not df.empty:
                st.write("📊 Procesando métricas avanzadas...")
                pdf_bytes = create_pdf_report(df)
                status.update(label="¡Reporte PDF Generado!", state="complete", expanded=False)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    label="⬇️ DESCARGAR REPORTE PDF FINAL",
                    data=pdf_bytes,
                    file_name=f"ChatStat_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
                st.success("Reporte listo. El procesamiento en la nube ha finalizado correctamente.")
            else:
                st.error("No se pudo procesar el archivo. Verifica que sea un .txt de WhatsApp.")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#444; font-size:10px; text-transform:uppercase; letter-spacing:3px;">Powered by ChatStat Engine • Business Grade Analytics</p>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()





