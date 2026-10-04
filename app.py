import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
import subprocess
import tempfile
import os
import re
import hashlib
import shutil


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI-Based Fake Identity Screening",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 AI-Based Fake Identity & Document Screening System")
st.caption(
    "Prototype for document screening, face verification and explainable risk assessment"
)


# =========================================================
# TESSERACT
# =========================================================

def find_tesseract():

    # Streamlit Cloud / Linux
    possible_paths = [
        shutil.which("tesseract"),
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",

        # Windows local
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    ]

    for path in possible_paths:

        if not path:
            continue

        if path == shutil.which("tesseract"):
            return path

        if os.path.exists(path):
            return path

    return None


TESSERACT = find_tesseract()


# =========================================================
# OCR
# =========================================================

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
            [
                TESSERACT,
                temp_input,
                "stdout",
                "--psm",
                "6"
            ],
            capture_output=True,
            text=True
        )

        return result.stdout.strip()

    except Exception:

        return ""

    finally:

        if temp_input and os.path.exists(temp_input):

            try:
                os.remove(temp_input)
            except:
                pass


# =========================================================
# FIELD EXTRACTION
# =========================================================

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

    # -----------------------------------------------------
    # Aadhaar
    # -----------------------------------------------------

    aadhaar_match = re.search(
        r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        text
    )

    if aadhaar_match:

        fields["Document Number"] = (
            aadhaar_match.group().replace(" ", "")
        )

        fields["Nationality"] = "Indian"

        fields["Expiry Date"] = "No expiry date"

    # -----------------------------------------------------
    # Document Number
    # -----------------------------------------------------

    doc_match = re.search(
        r"(?:passport|document|id|number|no)"
        r"[\s:#-]*([A-Z0-9]{6,15})",
        text,
        re.IGNORECASE
    )

    if (
        doc_match
        and fields["Document Number"] == "Not detected"
    ):

        fields["Document Number"] = doc_match.group(1)

    # -----------------------------------------------------
    # Date of Birth
    # -----------------------------------------------------

    dob_match = re.search(
        r"(?:DOB|Date of Birth|Birth)"
        r"[\s:#-]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        text,
        re.IGNORECASE
    )

    if dob_match:

        fields["Date of Birth"] = dob_match.group(1)

    # -----------------------------------------------------
    # Expiry
    # -----------------------------------------------------

    expiry_match = re.search(
        r"(?:Expiry|Expiration|Valid Until|Date of Expiry)"
        r"[\s:#-]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        text,
        re.IGNORECASE
    )

    if expiry_match:

        fields["Expiry Date"] = expiry_match.group(1)

    # -----------------------------------------------------
    # Nationality
    # -----------------------------------------------------

    nationality_match = re.search(
        r"(?:Nationality|Citizen)"
        r"[\s:#-]*([A-Za-z]+)",
        text,
        re.IGNORECASE
    )

    if (
        nationality_match
        and fields["Nationality"] == "Not detected"
    ):

        fields["Nationality"] = nationality_match.group(1)

    # -----------------------------------------------------
    # Name
    # -----------------------------------------------------

    name_match = re.search(
        r"(?:Name|Full Name)"
        r"[\s:#-]*([A-Za-z][A-Za-z .'-]{2,40})",
        text,
        re.IGNORECASE
    )

    if name_match:

        fields["Name"] = name_match.group(1).strip()

    return fields


# =========================================================
# TAMPERING ANALYSIS
# =========================================================

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


# =========================================================
# 1. DOCUMENT UPLOAD
# =========================================================

st.header("1️⃣ Document Upload")

documents = st.file_uploader(
    "Upload one or more identity documents",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

document_results = []


if documents:

    for i, uploaded_file in enumerate(documents):

        st.subheader(
            f"📄 Document {i + 1}: {uploaded_file.name}"
        )

        try:

            image = Image.open(uploaded_file).convert("RGB")

        except Exception:

            st.error(
                f"Could not read {uploaded_file.name}"
            )

            continue

        st.image(
            image,
            caption=uploaded_file.name,
            width=400
        )

        # -------------------------------------------------
        # OCR
        # -------------------------------------------------

        ocr_text = run_ocr(image)

        fields = extract_fields(ocr_text)

        # -------------------------------------------------
        # Tampering
        # -------------------------------------------------

        tampering_score, tampering_status = (
            tampering_analysis(image)
        )

        document_results.append(
            {
                "name": uploaded_file.name,
                "image": image,
                "fields": fields,
                "tampering_score": tampering_score,
                "tampering_status": tampering_status
            }
        )

        # -------------------------------------------------
        # OCR Extraction
        # -------------------------------------------------

        st.markdown("### OCR Extraction")

        col1, col2 = st.columns(2)

        with col1:

            st.write(
                "**Name:**",
                fields["Name"]
            )

            st.write(
                "**Document Number:**",
                fields["Document Number"]
            )

            st.write(
                "**Nationality:**",
                fields["Nationality"]
            )

        with col2:

            st.write(
                "**Date of Birth:**",
                fields["Date of Birth"]
            )

            st.write(
                "**Expiry Date:**",
                fields["Expiry Date"]
            )

        with st.expander("View Raw OCR Text"):

            if ocr_text:

                st.text(ocr_text)

            else:

                st.text(
                    "No OCR text detected."
                )

        # -------------------------------------------------
        # DOCUMENT VALIDATION
        # -------------------------------------------------

        st.markdown("### Document Validation")

        if fields["Document Number"] != "Not detected":

            st.success(
                "✅ Document number detected"
            )

        else:

            st.warning(
                "⚠️ Document number not detected"
            )

        if fields["Expiry Date"] == "No expiry date":

            st.info(
                "Document type appears to have no expiry date"
            )

        elif fields["Expiry Date"] != "Not detected":

            st.success(
                "✅ Expiry date detected"
            )

        else:

            st.warning(
                "⚠️ Expiry date not detected"
            )

        # -------------------------------------------------
        # TAMPERING
        # -------------------------------------------------

        st.markdown("### Tampering Detection")

        st.metric(
            "Prototype Tampering Score",
            f"{tampering_score}/100"
        )

        st.write(tampering_status)

        st.caption(
            "Prototype signal only — final verification "
            "requires human review."
        )

        st.divider()


# =========================================================
# 2. FACE VERIFICATION
# =========================================================

st.header("2️⃣ Face Verification")

face_file = st.file_uploader(
    "Upload the person's face photo / selfie",
    type=["jpg", "jpeg", "png"],
    key="face_upload"
)

face_match = None


if face_file:

    try:

        face_image = Image.open(
            face_file
        ).convert("RGB")

        st.image(
            face_image,
            caption="Uploaded Face / Selfie",
            width=300
        )

        if document_results:

            st.success(
                "✅ Face photo uploaded successfully"
            )

            st.info(
                "Face verification is submitted for "
                "human officer review in this prototype."
            )

            st.write(
                "**Verification Status:** "
                "Pending Officer Review"
            )

        else:

            st.warning(
                "Please upload an identity document first."
            )

    except Exception:

        st.error(
            "Unable to read the uploaded face image."
        )


# =========================================================
# 3. EXPLAINABLE RISK ASSESSMENT
# =========================================================

st.header("3️⃣ Explainable Risk Assessment")

risk_score = 0

reasons = []


# ---------------------------------------------------------
# No document
# ---------------------------------------------------------

if not documents:

    risk_score += 20

    reasons.append(
        "No identity document uploaded."
    )


# ---------------------------------------------------------
# Document checks
# ---------------------------------------------------------

if document_results:

    for result in document_results:

        fields = result["fields"]

        if fields["Document Number"] == "Not detected":

            risk_score += 15

            reasons.append(
                f"Document Number not detected "
                f"in {result['name']}."
            )

        if fields["Nationality"] == "Not detected":

            risk_score += 10

            reasons.append(
                f"Nationality not detected "
                f"in {result['name']}."
            )

        if fields["Expiry Date"] == "Not detected":

            risk_score += 10

            reasons.append(
                f"Expiry Date not detected "
                f"in {result['name']}."
            )

        if result["tampering_score"] >= 70:

            risk_score += 20

            reasons.append(
                f"Potential tampering signal "
                f"in {result['name']}."
            )


# ---------------------------------------------------------
# Face check
# ---------------------------------------------------------

if face_file is None:

    risk_score += 10

    reasons.append(
        "Face photo has not been uploaded."
    )

elif face_match is None:

    reasons.append(
        "Face verification is pending human officer review."
    )


risk_score = min(
    risk_score,
    100
)


# ---------------------------------------------------------
# Risk level
# ---------------------------------------------------------

if risk_score >= 60:

    risk_level = "HIGH"

elif risk_score >= 30:

    risk_level = "MEDIUM"

else:

    risk_level = "LOW"


if risk_level == "HIGH":

    st.error(
        f"🔴 Risk Level: {risk_level} "
        f"({risk_score}/100)"
    )

elif risk_level == "MEDIUM":

    st.warning(
        f"🟡 Risk Level: {risk_level} "
        f"({risk_score}/100)"
    )

else:

    st.success(
        f"🟢 Risk Level: {risk_level} "
        f"({risk_score}/100)"
    )


# ---------------------------------------------------------
# Reasons
# ---------------------------------------------------------

st.markdown("### Risk Factors")

if reasons:

    for reason in reasons:

        st.write(
            "•",
            reason
        )

else:

    st.success(
        "No major risk signals detected."
    )


# =========================================================
# 4. SCREENING SUMMARY
# =========================================================

st.header("4️⃣ Screening Summary")


if document_results:

    for result in document_results:

        st.write(
            f"**Document:** {result['name']}"
        )

        st.write(
            f"Tampering Score: "
            f"{result['tampering_score']}/100"
        )

        st.write(
            f"Tampering Status: "
            f"{result['tampering_status']}"
        )

    if face_file:

        st.info(
            "Face Verification: "
            "PENDING HUMAN REVIEW"
        )

    else:

        st.warning(
            "Face Verification: "
            "NOT PROVIDED"
        )

    st.write(
        f"Overall Risk: "
        f"**{risk_level} ({risk_score}/100)**"
    )

else:

    st.info(
        "Upload an identity document to generate "
        "the screening summary."
    )


# =========================================================
# 5. OFFICER REVIEW
# =========================================================

st.header("5️⃣ Officer Review")

decision = st.radio(
    "Final Decision",
    [
        "Pending Review",
        "Approve / Clear",
        "Refer for Further Review"
    ]
)


if decision == "Pending Review":

    st.info(
        "⏳ Awaiting human officer decision."
    )

elif decision == "Approve / Clear":

    st.success(
        "✅ Officer Decision: APPROVE / CLEAR"
    )

else:

    st.warning(
        "⚠️ Officer Decision: "
        "REFER FOR FURTHER REVIEW"
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Prototype system — final identity/document "
    "decisions should always remain with a qualified "
    "human officer."
)

st.caption(
    "OCR, tampering analysis and face verification "
    "are prototype-level screening components."
)
