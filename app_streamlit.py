


import streamlit as st
from PIL import Image
import io
import requests
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

BACKEND_URL = "http://127.0.0.1:8000/PredictFull"

# ------------------ Functions ------------------
def send_to_backend(image_bytes, filename, mime_type, sex=None, age=None, height=None, weight=None):
    files = {"file": (filename, image_bytes, mime_type)}
    data = {}
    if sex: data["Sex"] = sex
    if age: data["Age"] = str(age)
    if height: data["Height"] = str(height)
    if weight: data["Weight"] = str(weight)
    try:
        response = requests.post(BACKEND_URL, files=files, data=data)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# PDF report generation function (same as your code)
def generate_pdf_report(child_name, age, gender, height, weight, results):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#0066cc'), alignment=1, fontName='Helvetica-Bold')
    story.append(Paragraph("🏥 Malnutrition Detection Report", title_style))
    story.append(Spacer(1, 0.2 * inch))

    report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info_data = [["Report Date:", report_date], ["Child Name:", child_name], ["Age:", f"{age} years"], ["Gender:", gender], ["Height:", f"{height} cm"], ["Weight:", f"{weight} kg"]]
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f7ff')), ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'), ('GRID', (0, 0), (-1, -1), 1, colors.grey)]))
    story.append(info_table)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("🧠 Prediction Results", styles['Heading2']))
    results_table = Table([["Image Prediction:", results.get("Image Prediction", "N/A")], ["Numeric Prediction:", str(results.get("Numeric Prediction", "N/A"))], ["Advice:", results.get("Advice", "No advice provided.")]], colWidths=[2*inch, 4*inch])
    results_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f9f9f9')), ('GRID', (0, 0), (-1, -1), 1, colors.grey)]))
    story.append(results_table)

    disclaimer = Paragraph("<b>Disclaimer:</b> This report is for informational purposes only. Always consult a healthcare professional for accurate diagnosis.", styles['Normal'])
    story.append(Spacer(1, 0.2 * inch))
    story.append(disclaimer)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ------------------ Streamlit UI ------------------
st.set_page_config(page_title="MedAssess - Malnutrition Detection", page_icon="🏥", layout="wide")
st.markdown("<h1 style='text-align:center;color:#5a5ddf;'>🏥 MedAssess - Malnutrition Detection System</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Upload a child’s image and get a real AI-powered nutrition assessment.</p>", unsafe_allow_html=True)
st.write("---")

uploaded_file = st.file_uploader("📸 Upload Child's Image", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    if "uploaded_name" not in st.session_state or st.session_state.uploaded_name != uploaded_file.name:
        st.session_state.image_bytes = uploaded_file.read()
        st.session_state.filename = uploaded_file.name
        st.session_state.mime_type = uploaded_file.type
        st.session_state.uploaded_name = uploaded_file.name
        st.session_state.image_result = None
        st.session_state.full_result = None

    image = Image.open(io.BytesIO(st.session_state.image_bytes))
    st.image(image, caption="Uploaded Image", width=300)

    if st.button("🔍 Analyze Image"):
        result = send_to_backend(st.session_state.image_bytes, st.session_state.filename, st.session_state.mime_type)
        if result:
            st.session_state.image_result = result
            st.success(f"✅ Image Prediction: {result.get('Image Prediction', 'Unknown')}")
            if result.get('Image Prediction', '').lower() == "malnourished":
                st.warning("⚠️ Please enter biometric data for detailed analysis.")

    if st.session_state.image_result and st.session_state.image_result.get("Image Prediction", "").lower() == "malnourished":
        st.write("---")
        st.subheader("📊 Provide Biometric Data")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Child's Name", "")
            gender = st.selectbox("Gender", ["Male", "Female"])
            age = st.number_input("Age (years)", min_value=0, max_value=5, step=1)
        with col2:
            height = st.number_input("Height (cm)", min_value=40.0, max_value=120.0, step=0.1)
            weight = st.number_input("Weight (kg)", min_value=2.0, max_value=30.0, step=0.1)

        if st.button("📋 Generate Detailed Report"):
            result = send_to_backend(st.session_state.image_bytes, st.session_state.filename, st.session_state.mime_type, sex=gender, age=age, height=height, weight=weight)
            if result:
                st.session_state.full_result = result
                st.success("✅ Report generated successfully!")
                st.write("### 🧾 Prediction Summary")
                st.write(f"**Image Prediction:** {result.get('Image Prediction', 'N/A')}")
                st.write(f"**Numeric Prediction:** {result.get('Numeric Prediction', 'N/A')}")
                st.write(f"**Advice:** {result.get('Advice', 'N/A')}")
                pdf_buffer = generate_pdf_report(name, age, gender, height, weight, result)
                st.download_button("📥 Download PDF Report", data=pdf_buffer, file_name=f"malnutrition_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", mime="application/pdf")
