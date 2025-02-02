import streamlit as st
import PyPDF2
from PyPDF2 import PdfReader, PdfWriter
import zipfile
import io
import calendar
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import pdfplumber
import os

# Configuración de la página
st.set_page_config(page_title="Procesador de PDFs Automático", layout="wide")

# Crear pestañas
tab1, tab2, tab3 = st.tabs(["Bienvenida", "Dividir Documento", "Completar Documento"])

# Sección de Bienvenida
with tab1:
    st.markdown("""
    <h1 style='text-align: center;'>Procesador de PDFs Automático</h1>
    """, unsafe_allow_html=True)

    try:
        # Intentar cargar la imagen localmente
        st.image("AutoPDF_transparent-.png", caption="Logo de Colaboring Barcelona SL", width=400)
    except Exception as e:
        # Si falla, cargar una imagen desde una URL pública
        st.image("AutoPDF-.png", caption="Logo de Colaboring Barcelona SL", width=150)

    st.markdown("""
    <p style='text-align: center;'>
    Bienvenido al Procesador de PDFs Automático. Esta herramienta te permite:
    - Dividir un archivo PDF en múltiples documentos individuales.
    - Completar automáticamente los registros de jornada laboral con horarios predefinidos.
    </p>
    """, unsafe_allow_html=True)

# Función para dividir el PDF por páginas y guardar por nombre del trabajador
def split_pdf_by_worker(pdf_path):
    with open(pdf_path, "rb") as file:
        reader = PdfReader(file)
        num_pages = len(reader.pages)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for page_num in range(num_pages):
                writer = PdfWriter()
                writer.add_page(reader.pages[page_num])

                with pdfplumber.open(pdf_path) as plumber:
                    text = plumber.pages[page_num].extract_text()
                    if "Trabajador:" in text:
                        worker_name = text.split("Trabajador:")[1].split("\n")[0].strip().replace(" ", "_")
                    else:
                        worker_name = f"pagina_{page_num + 1}"

                output_filename = f"{worker_name}.pdf"
                with io.BytesIO() as temp_buffer:
                    writer.write(temp_buffer)
                    temp_buffer.seek(0)
                    zip_file.writestr(output_filename, temp_buffer.read())

    return zip_buffer, num_pages

# Función para generar una tabla con los horarios
def generate_schedule(year, month, holidays):
    cal = calendar.Calendar()
    weekdays = [(day, weekday) for day, weekday in cal.itermonthdays2(year, month) if day != 0]

    data = [
        ["DIA", "MAÑANAS ENTRADA", "MAÑANAS SALIDA", "TARDES ENTRADA", "TARDES SALIDA", "HORAS ORDINARIAS"]
    ]

    total_hours = 0
    for day, weekday in weekdays:
        if weekday < 5 and day not in holidays:  # Solo días laborables
            morning_entry = "08:00"
            morning_exit = "14:00"
            afternoon_entry = "15:00"
            afternoon_exit = "18:00"
            hours = 8
            total_hours += hours
        else:
            morning_entry = ""
            morning_exit = ""
            afternoon_entry = ""
            afternoon_exit = ""
            hours = ""

        data.append([str(day), morning_entry, morning_exit, afternoon_entry, afternoon_exit, str(hours)])

    data.append(["TOTAL", "", "", "", "", str(total_hours)])

    table = Table(data, colWidths=[40, 70, 70, 70, 70, 40])  # Ajustar el ancho de las columnas
    style = TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Fondo de la cabecera
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Color del texto en la cabecera
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Alineación centrada para toda la tabla
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Fuente negrita para la cabecera
    ('FONTSIZE', (0, 0), (-1, 0), 7),  # Reducir el tamaño de fuente en la cabecera
    ('BOTTOMPADDING', (0, 0), (-1, 0), 3),  # Reducir el padding inferior de la cabecera
    ('TOPPADDING', (0, 0), (-1, 0), 3),  # Reducir el padding superior de la cabecera
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  # Fondo para el resto de la tabla
    ('FONTSIZE', (0, 1), (-1, -1), 6),  # Reducir el tamaño de fuente para el cuerpo de la tabla
    ('BOTTOMPADDING', (0, 1), (-1, -1), 2),  # Reducir el padding inferior de las filas
    ('TOPPADDING', (0, 1), (-1, -1), 2),  # Reducir el padding superior de las filas
    ('ROWHEIGHT', (0, 1), (-1, -1), 15),  # Ajustar la altura de las filas (valor en puntos)
    ])
    table.setStyle(style)

    return table

# Superponer la tabla sobre el PDF
def overlay_table_on_pdf(input_pdf, output_pdf, table):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    width, height = letter

    table_width = sum(table._colWidths)  # Ancho total de la tabla
    x_position = ((width - table_width) / 2)-2  # Posición x para centrar
    y_position = height - 500  # Ajustar la posición vertical más abajo

    table.wrapOn(can, width, height)
    table.drawOn(can, x_position, y_position)
    can.save()

    packet.seek(0)
    new_pdf = PdfReader(packet)

    existing_pdf = PdfReader(input_pdf)
    output = PdfWriter()

    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)

    with open(output_pdf, "wb") as output_file:
        output.write(output_file)

# Sección "Dividir Documento"
with tab2:
    st.markdown("""
    <h2 style='text-align: center;'>Dividir Documento</h2>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Sube tu archivo PDF para dividirlo", type=["pdf"])
    if uploaded_file is not None:
        temp_pdf_path = "temp.pdf"
        with open(temp_pdf_path, "wb") as temp_file:
            temp_file.write(uploaded_file.read())

        zip_buffer, num_pages = split_pdf_by_worker(temp_pdf_path)
        st.success(f"El PDF ha sido dividido en {num_pages} páginas.")

        st.download_button(
            label="Descargar archivos divididos",
            data=zip_buffer.getvalue(),
            file_name="documentos_divididos.zip",
            mime="application/zip"
        )

        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

# Sección "Completar Documento"
with tab3:
    st.markdown("""
    <h2 style='text-align: center;'>Completar Documento</h2>
    """, unsafe_allow_html=True)

    uploaded_file_individual = st.file_uploader("Sube un archivo PDF individual para completarlo", type=["pdf"])
    if uploaded_file_individual is not None:
        temp_individual_pdf_path = "temp_individual.pdf"
        with open(temp_individual_pdf_path, "wb") as temp_file:
            temp_file.write(uploaded_file_individual.read())

        year = 2025
        month = 1
        holidays = [1, 6]  # Festivos en Barcelona

        schedule_table = generate_schedule(year, month, holidays)
        output_pdf_path = "output_completed.pdf"
        overlay_table_on_pdf(temp_individual_pdf_path, output_pdf_path, schedule_table)
        st.success("El PDF ha sido procesado correctamente.")

        with open(output_pdf_path, "rb") as file:
            btn = st.download_button(
                label="Descargar PDF completado",
                data=file,
                file_name="output_completed.pdf",
                mime="application/pdf"
            )

        if os.path.exists(temp_individual_pdf_path):
            os.remove(temp_individual_pdf_path)
        if os.path.exists(output_pdf_path):
            os.remove(output_pdf_path)