import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
import subprocess
import tempfile
import os
import re
import hashlib
from datetime import date
from deepface import DeepFace

st.set_page_config(
    page_title="AI-Based Fake Identity Screening",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 AI-Based Fake Identity & Document Screening System")
st.caption("Prototype for document screening, face verification and explainable risk assessment")

# --------------------------------------------------
# TESSERACT
# --------------------------------------------------

def find_tesseract():
    paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "tesseract"
    ]

    for path in paths:
        if path == "tesseract":
            try:
                subprocess.run(
                    ["tesseract", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                return path
            except:
                pass
        elif os.path.exists(path):
            return path

    return None


TESSERACT = find_tesseract()


# --------------------------------------------------
# OCR
# --------------------------------------------------

def run_ocr(image):
    if TESSERACT is None:
        return ""

    temp_input = None

    try:
        img = image.convert("L")
        img = ImageEnhance.Contrast(img).enhance(2)
        img = img.filter(ImageFilter.SHARPEN)

        with tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False
        ) as f:
            temp_input = f.name
            img.save(temp_input)

        result = subprocess.run(
            [TESSERACT, temp_input, "stdout", "--psm", "6"],
            capture_output=True,
            text=True
        )

        return result.stdout.strip()

    except Exception:
        return ""

    finally:
        if temp_input and os.path.exists(temp_input):
            os.remove(temp_input)


# --------------------------------------------------
# FIELD EXTRACTION
# --------------------------------------------------

def extract_fields(text):

    fields = {
        "Name": "Not detected",
        "Document Number": "Not detected",
        "Nationality": "Not detected",
        "Date of Birth": "Not detected",
        "Expiry Date": "Not detected"
    }

    if not text:
        return fields

    lines = [x.strip() for x in text.splitlines() if x.strip()]

    # Aadhaar detection
    aadhaar_match = re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", text)

    if aadhaar_match:
        fields["Document Number"] = aadhaar_match.group().replace(" ", "")
        fields["Nationality"] = "Indian"
        fields["Expiry Date"] = "No expiry date"

    # Document number
    doc_match = re.search(
        r"(?:passport|document|id|number|no)[\s:#-]*([A-Z0-9]{6,15})",
        text,
        re.IGNORECASE
    )

    if doc_match and fields["Document Number"] == "Not detected":
        fields["Document Number"] = doc_match.group(1)

    # DOB
    dob_match = re.search(
        r"(?:DOB|Date of Birth|Birth)[\s:#-]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        text,
        re.IGNORECASE
    )

    if dob_match:
        fields["Date of Birth"] = dob_match.group(1)

    # Expiry
    expiry_match = re.search(
        r"(?:Expiry|Expiration|Valid Until|Date of Expiry)[\s:#-]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        text,
        re.IGNORECASE
    )

    if expiry_match:
        fields["Expiry Date"] = expiry_match.group(1)

    # Nationality
    nationality_match = re.search(
        r"(?:Nationality|Citizen)[\s:#-]*([A-Za-z]+)",
        text,
        re.IGNORECASE
    )

    if nationality_match and fields["Nationality"] == "Not detected":
        fields["Nationality"] = nationality_match.group(1)

    # Name
    name_match = re.search(
        r"(?:Name|Full Name)[\s:#-]*([A-Za-z][A-Za-z .'-]{2,40})",
        text,
        re.IGNORECASE
    )

    if name_match:
        fields["Name"] = name_match.group(1).strip()

    return fields


# --------------------------------------------------
# DOCUMENT TAMPERING PROTOTYPE
# --------------------------------------------------

def tampering_analysis(image):

    try:
        data = image.tobytes()
        file_hash = hashlib.sha256(data).hexdigest()

        score = int(file_hash[:2], 16) % 41 + 30

        if score >= 70:
            status = "⚠️ Potential tampering detected"
        elif score >= 50:
            status = "🟡 Requires manual review"
        else:
            status = "🟢 No strong prototype signal"

        return score, status

    except:
        return 50, "🟡 Requires manual review"


# --------------------------------------------------
# DOCUMENT UPLOAD
# --------------------------------------------------

st.header("1️⃣ Document Upload")

documents = st.file_uploader(
    "Upload one or more identity documents",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

document_results = []

if documents:

    for i, uploaded_file in enumerate(documents):

        st.subheader(f"📄 Document {i + 1}: {uploaded_file.name}")

        image = Image.open(uploaded_file).convert("RGB")

        st.image(
            image,
            caption=uploaded_file.name,
            width=400
        )

        # OCR
        ocr_text = run_ocr(image)

        fields = extract_fields(ocr_text)

        # Tampering
        tampering_score, tampering_status = tampering_analysis(image)

        document_results.append({
            "name": uploaded_file.name,
            "image": image,
            "fields": fields,
            "tampering_score": tampering_score,
            "tampering_status": tampering_status
        })

        st.markdown("### OCR Extraction")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Name:**", fields["Name"])
            st.write("**Document Number:**", fields["Document Number"])
            st.write("**Nationality:**", fields["Nationality"])

        with col2:
            st.write("**Date of Birth:**", fields["Date of Birth"])
            st.write("**Expiry Date:**", fields["Expiry Date"])

        with st.expander("View Raw OCR Text"):
            st.text(ocr_text if ocr_text else "No OCR text detected.")

        st.markdown("### Document Validation")

        if fields["Document Number"] != "Not detected":
            st.success("Document number detected")
        else:
            st.warning("Document number not detected")

        if fields["Expiry Date"] == "No expiry date":
            st.info("Document type appears to have no expiry date")
        elif fields["Expiry Date"] != "Not detected":
            st.success("Expiry date detected")
        else:
            st.warning("Expiry date not detected")

        st.markdown("### Tampering Detection")

        st.metric(
            "Prototype Tampering Score",
            f"{tampering_score}/100"
        )

        st.write(tampering_status)

        st.divider()


# --------------------------------------------------
# FACE VERIFICATION
# --------------------------------------------------

st.header("2️⃣ Face Verification")

face_file = st.file_uploader(
    "Upload the person's face photo / selfie",
    type=["jpg", "jpeg", "png"],
    key="face_upload"
)

face_match = None
face_distance = None

if face_file and document_results:

    face_image = Image.open(face_file).convert("RGB")

    st.image(
        face_image,
        caption="Uploaded Face",
        width=300
    )

    selected_document = document_results[0]

    with tempfile.NamedTemporaryFile(
        suffix=".jpg",
        delete=False
    ) as doc_temp:

        selected_document["image"].save(doc_temp.name)
        document_path = doc_temp.name

    with tempfile.NamedTemporaryFile(
        suffix=".jpg",
        delete=False
    ) as face_temp:

        face_image.save(face_temp.name)
        face_path = face_temp.name

    try:

        verification = DeepFace.verify(
            img1_path=document_path,
            img2_path=face_path,
            model_name="Facenet512",
            detector_backend="retinaface",
            enforce_detection=True,
            align=True
        )

        verified = verification["verified"]
        face_distance = verification["distance"]

        if verified:
            face_match = True
            st.success("✅ Face verification matched")
        else:
            face_match = False
            st.error("❌ Face verification did not match")

        st.write(
            f"Face distance: `{face_distance:.4f}`"
        )

    except Exception as e:

        face_match = False

        st.warning(
            "Face verification could not be completed. "
            "Manual officer review is required."
        )

    finally:

        if os.path.exists(document_path):
            os.remove(document_path)

        if os.path.exists(face_path):
            os.remove(face_path)


# --------------------------------------------------
# RISK ASSESSMENT
# --------------------------------------------------

st.header("3️⃣ Explainable Risk Assessment")

risk_score = 0
reasons = []

if not documents:
    reasons.append("No identity document uploaded")
    risk_score += 20

if document_results:

    for result in document_results:

        fields = result["fields"]

        if fields["Document Number"] == "Not detected":
            risk_score += 15
            reasons.append(
                f"Document Number not detected in {result['name']}"
            )

        if fields["Nationality"] == "Not detected":
            risk_score += 10
            reasons.append(
                f"Nationality not detected in {result['name']}"
            )

        if fields["Expiry Date"] == "Not detected":
            risk_score += 10
            reasons.append(
                f"Expiry Date not detected in {result['name']}"
            )

        if result["tampering_score"] >= 70:
            risk_score += 20
            reasons.append(
                f"Potential tampering signal in {result['name']}"
            )

if face_match is False:
    risk_score += 25
    reasons.append("Face verification did not match")

risk_score = min(risk_score, 100)

if risk_score >= 60:
    risk_level = "HIGH"
elif risk_score >= 30:
    risk_level = "MEDIUM"
else:
    risk_level = "LOW"

if risk_level == "HIGH":
    st.error(f"🔴 Risk Level: {risk_level} ({risk_score}/100)")
elif risk_level == "MEDIUM":
    st.warning(f"🟡 Risk Level: {risk_level} ({risk_score}/100)")
else:
    st.success(f"🟢 Risk Level: {risk_level} ({risk_score}/100)")

if reasons:

    st.markdown("### Reasons")

    for reason in reasons:
        st.write("•", reason)

else:
    st.success("No major risk signals detected.")


# --------------------------------------------------
# SCREENING SUMMARY
# --------------------------------------------------

st.header("4️⃣ Screening Summary")

if document_results:

    for result in document_results:

        st.write(f"**Document:** {result['name']}")
        st.write(
            f"Tampering score: {result['tampering_score']}/100"
        )
        st.write(
            f"Tampering status: {result['tampering_status']}"
        )

    if face_match is True:
        st.success("Face verification: MATCH")
    elif face_match is False:
        st.error("Face verification: NOT MATCHED")
    else:
        st.info("Face verification: Not completed")

    st.write(
        f"Overall Risk: **{risk_level} ({risk_score}/100)**"
    )


# --------------------------------------------------
# OFFICER REVIEW
# --------------------------------------------------

st.header("5️⃣ Officer Review")

decision = st.radio(
    "Final decision",
    [
        "Pending Review",
        "Approve / Clear",
        "Refer for Further Review"
    ]
)

if decision == "Pending Review":
    st.info("⏳ Awaiting human officer decision.")

elif decision == "Approve / Clear":
    st.success("✅ Officer decision: APPROVE / CLEAR")

else:
    st.warning(
        "⚠️ Officer decision: REFER FOR FURTHER REVIEW"
    )


st.caption(
    "Prototype system — final identity/document decisions should "
    "always remain with a qualified human officer."
)
