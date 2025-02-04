import streamlit as st
import calendar
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import pdfplumber
import io
from PyPDF2 import PdfReader, PdfWriter
import os

# Festivos predefinidos para Barcelona
barcelona_holidays = {
    2024: ["01-01", "06-01", "29-03", "01-04", "01-05", "24-06", "15-08", "11-09", "24-09", "12-10", "01-11", "06-12", "08-12", "25-12", "26-12"],
    2025: ["01-01", "06-01", "18-04", "21-04", "01-05", "24-06", "15-08", "11-09", "24-09", "12-10", "01-11", "06-12", "08-12", "25-12", "26-12"]
}

# Función para generar la tabla de horarios excluyendo fines de semana y festivos
def generate_schedule(month, year):
    cal = calendar.Calendar()
    weekdays = [(day, weekday) for day, weekday in cal.itermonthdays2(year, month) if day != 0]
    
    # Obtener los festivos en formato "dd-mm"
    holiday_set = {f"{day}" for day in barcelona_holidays.get(year, [])}

    data = [["DIA", "MAÑANAS ENTRADA", "MAÑANAS SALIDA", "TARDES ENTRADA", "TARDES SALIDA", "HORAS ORDINARIAS"]]
    total_hours = 0

    for day, weekday in weekdays:
        day_str = f"{day:02d}-{month:02d}"  # Formato dd-mm

        # Solo agregar si no es fin de semana ni festivo
        if weekday < 5 and day_str not in holiday_set:
            morning_entry = "08:00"
            morning_exit = "14:00"
            afternoon_entry = "15:00"
            afternoon_exit = "18:00"
            hours = 8
            total_hours += hours
        else:
            morning_entry = morning_exit = afternoon_entry = afternoon_exit = hours = ""

        data.append([str(day), morning_entry, morning_exit, afternoon_entry, afternoon_exit, str(hours)])

    data.append(["TOTAL", "", "", "", "", str(total_hours)])

    # Crear tabla
    table = Table(data[1:], colWidths=[60, 80, 80, 80, 80, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
        ('TOPPADDING', (0, 0), (-1, 0), 3),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
        ('TOPPADDING', (0, 1), (-1, -1), 2),
        ('ROWHEIGHT', (0, 1), (-1, -1), 15),
    ]))

    return table

# Función para detectar mes y año en PDF
def extract_month_year(pdf_path):
    with pdfplumber.open(pdf_path) as plumber:
        first_page_text = plumber.pages[0].extract_text()
        if "Mes y Año:" in first_page_text:
            month_year_str = first_page_text.split("Mes y Año:")[1].split("\n")[0].strip()
            try:
                month, year = map(int, month_year_str.split("/"))
                return month, year
            except ValueError:
                st.error("No se pudo extraer el mes y año correctamente del PDF.")
    return None, None

# Superponer tabla en el PDF
def overlay_table_on_pdf(input_pdf, output_pdf, table):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    width, height = letter

    table_width = sum(table._colWidths)
    x_position = (width - table_width) / 2 - 75
    y_position = height - 600

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

# Streamlit UI
st.set_page_config(page_title="Procesador de PDFs", layout="wide")
st.markdown("<h1 style='text-align: center;'>Procesador de PDFs Automático</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Dividir Documento", "Completar Documento"])

# Sección "Completar Documento"
with tab2:
    st.markdown("<h2 style='text-align: center;'>Completar Documento</h2>", unsafe_allow_html=True)
    uploaded_file_individual = st.file_uploader("Sube un archivo PDF individual para completarlo", type=["pdf"])

    if uploaded_file_individual is not None:
        temp_individual_pdf_path = "temp_individual.pdf"
        with open(temp_individual_pdf_path, "wb") as temp_file:
            temp_file.write(uploaded_file_individual.read())

        # Detectar mes y año del PDF
        month, year = extract_month_year(temp_individual_pdf_path)
        if month is None or year is None:
            st.error("No se pudo determinar el mes y año del PDF.")
        else:
            st.info(f"Se detectó el mes {calendar.month_name[month]} del año {year}.")

            # Generar la tabla de horarios
            schedule_table = generate_schedule(month, year)
            output_pdf_path = "output_completed.pdf"
            overlay_table_on_pdf(temp_individual_pdf_path, output_pdf_path, schedule_table)
            st.success("El PDF ha sido procesado correctamente.")

            with open(output_pdf_path, "rb") as file:
                st.download_button(label="Descargar PDF completado", data=file, file_name="output_completed.pdf", mime="application/pdf")

        # Eliminar archivos temporales
        os.remove(temp_individual_pdf_path)
        os.remove(output_pdf_path)
