from flask import Flask, render_template, request, jsonify, send_file
import os
import time
import pickle
import re

# Google APIs
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread

# PDF
from weasyprint import HTML

app = Flask(__name__)

# ================= CONFIG =================

UPLOAD_FOLDER = "static/uploads"
PDF_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

SPREADSHEET_NAME = "Exit Form Data"
PARENT_FOLDER_ID = "1cZMLLfk18AErtc83J0xBOFejtxJJd1IG"

# ================= GOOGLE AUTH =================

import base64
import tempfile
import os

token_base64 = os.environ.get("GOOGLE_TOKEN")

if not token_base64:
    raise Exception("GOOGLE_TOKEN not found in environment variables")

temp_file = tempfile.NamedTemporaryFile(delete=False)
temp_file.write(base64.b64decode(token_base64))
temp_file.close()

with open(temp_file.name, "rb") as token:
    creds = pickle.load(token)

drive_service = build("drive", "v3", credentials=creds)
gc = gspread.authorize(creds)

# ================= SHEETS FUNCTION =================

def create_drive_folder(name, parent_id=None):
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder"
    }

    if parent_id:
        metadata["parents"] = [parent_id]

    folder = drive_service.files().create(
        body=metadata,
        fields="id"
    ).execute()

    return folder.get("id")

def sanitize_filename(name):
    name = name.strip().replace(" ", "_")
    name = re.sub(r'[^A-Za-z0-9_]', '', name)
    return name

def generate_emp_id():
    sheet = gc.open(SPREADSHEET_NAME).worksheet("Employee Data")

    records = sheet.get_all_values()

    if len(records) <= 1:
        return "EMP001"

    last_row = records[-1]
    last_id = last_row[0]

    try:
        num = int(last_id.replace("EMP", ""))
        return f"EMP{num + 1:03d}"
    except:
        return "EMP001"

def save_to_sheets_structured(data, drive_link, signature_url, emp_id):
    sheet = gc.open(SPREADSHEET_NAME)

    # ===== EMPLOYEE =====
    sheet.worksheet("Employee Data").append_row([
        emp_id,
        data.get("name"),
        data.get("contact"),
        data.get("manager"),
        data.get("date"),
        ", ".join(data.getlist("reason[]")),
        data.get("comments"),
        data.get("place"),
        data.get("sign_date"),
        drive_link,
        signature_url
    ])

    # ===== ARTICLESHIP =====
    sheet.worksheet("Articleship Feedback").append_row([
        emp_id,
        data.get("name"),
        data.get("q1"), data.get("q2"), data.get("q3"),
        data.get("q4"), data.get("q5"), data.get("q6"),
        data.get("q7"),
        data.get("improvement")
    ])

    # ===== REMUNERATION =====
    sheet.worksheet("Remuneration").append_row([
        emp_id,
        data.get("name"),
        data.get("r1"), data.get("r2"),
        data.get("r3"), data.get("r4"),
        data.get("benefits")
    ])

    # ===== KPCA =====
    sheet.worksheet("KPCA Feedback").append_row([
        emp_id,
        data.get("name"),
        *[data.get(f"kpca{i}") for i in range(1,10)],
        data.get("kpca_improvement")
    ])

    # ===== MANAGER =====
    sheet.worksheet("Manager Feedback").append_row([
        emp_id,
        data.get("name"),
        *[data.get(f"mgr{i}") for i in range(1,11)],
        data.get("mgr_feedback")
    ])

    # ===== ROTATION =====
    sheet.worksheet("Rotation Policy").append_row([
        emp_id,
        data.get("name"),
        data.get("rot1"),
        data.get("rot2"),
        data.get("rot3"),
        data.get("rotation_continue"),
        data.get("rotation_comments")
    ])


# ================= ROUTES =================

@app.route("/")
def home():
    return render_template("exit_form.html")


@app.route("/submit", methods=["POST"])
def submit():
    print("STEP 1 START")
    try:
        data = request.form
        # ================= BASIC DATA =================

        emp_id = generate_emp_id()
        name = data.get("name")
        contact = data.get("contact")
        manager = data.get("manager")
        date = data.get("date")

        # ================= FILE + FOLDER SETUP =================
        print("STEP 2 FOLDER")

        safe_name = sanitize_filename(name) if name else "User"

        pdf_filename = f"{emp_id}_{safe_name}.pdf"
        pdf_path = os.path.join(PDF_FOLDER, pdf_filename)

        main_folder_name = f"{emp_id}_{safe_name}"

        # CREATE FOLDERS
        main_folder_id = create_drive_folder(main_folder_name, PARENT_FOLDER_ID)
        pdf_folder_id = create_drive_folder("PDF", main_folder_id)
        signature_folder_id = create_drive_folder("Signature", main_folder_id)

        reasons = ", ".join(request.form.getlist("reason[]"))

        comments = data.get("comments", "").replace("\n", "<br>")
        improvement = data.get("improvement", "").replace("\n", "<br>")
        benefits = data.get("benefits", "").replace("\n", "<br>")
        kpca_improvement = data.get("kpca_improvement", "").replace("\n", "<br>")
        mgr_feedback = data.get("mgr_feedback", "").replace("\n", "<br>")
        rotation_comments = data.get("rotation_comments", "").replace("\n", "<br>")

        # ================= RATINGS =================

        q1,q2,q3,q4,q5,q6,q7 = [data.get(f"q{i}") for i in range(1,8)]
        r1,r2,r3,r4 = [data.get(f"r{i}") for i in range(1,5)]

        kpca = [data.get(f"kpca{i}") for i in range(1,10)]
        mgr = [data.get(f"mgr{i}") for i in range(1,11)]

        rot1 = data.get("rot1")
        rot2 = data.get("rot2")
        rot3 = data.get("rot3")
        rotation_continue = data.get("rotation_continue")

        place = data.get("place")
        sign_date = data.get("sign_date")

        # ================= SIGNATURE UPLOAD =================
        print("STEP 3 SIGNATURE")

        signature_url = ""

        signature_file = request.files.get("hr_signature_file")

        if signature_file and signature_file.filename:
            filename = f"{emp_id}_signature.png"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            signature_file.save(filepath)

            media = MediaFileUpload(filepath, mimetype="image/png")

            file = drive_service.files().create(
                body={
                    "name": filename,
                    "parents": [signature_folder_id]   # ✅ now exists
                },
                media_body=media,
                fields="id"
            ).execute()

            file_id = file.get("id")

            drive_service.permissions().create(
                fileId=file_id,
                body={"role": "reader", "type": "anyone"}
            ).execute()

            signature_url = f"https://drive.google.com/uc?id={file_id}"
            try:
                os.remove(filepath)
            except:
                pass
        # ================= PDF GENERATION =================
        print("STEP 4 PDF")
        html = render_template(
            "form_pdf.html",
            name=name, contact=contact, manager=manager, date=date,
            reasons=reasons, comments=comments,
            improvement=improvement, benefits=benefits,
            kpca_improvement=kpca_improvement,
            mgr_feedback=mgr_feedback,
            rotation_comments=rotation_comments,

            q1=q1,q2=q2,q3=q3,q4=q4,q5=q5,q6=q6,q7=q7,
            r1=r1,r2=r2,r3=r3,r4=r4,

            kpca1=kpca[0],kpca2=kpca[1],kpca3=kpca[2],
            kpca4=kpca[3],kpca5=kpca[4],kpca6=kpca[5],
            kpca7=kpca[6],kpca8=kpca[7],kpca9=kpca[8],

            mgr1=mgr[0],mgr2=mgr[1],mgr3=mgr[2],
            mgr4=mgr[3],mgr5=mgr[4],mgr6=mgr[5],
            mgr7=mgr[6],mgr8=mgr[7],mgr9=mgr[8],
            mgr10=mgr[9],

            rot1=rot1, rot2=rot2, rot3=rot3,
            rotation_continue=rotation_continue,

            place=place,
            sign_date=sign_date,
            signature_url=signature_url
        )

        HTML(string=html).write_pdf(pdf_path)

        # ================= UPLOAD PDF =================
        media = MediaFileUpload(pdf_path, mimetype="application/pdf")

        file = drive_service.files().create(
            body={
                "name": pdf_filename,
                "parents": [pdf_folder_id]   # 🔥 IMPORTANT
            },
            media_body=media,
            fields="id"
        ).execute()

        file_id = file.get("id")

        drive_service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"}
        ).execute()

        drive_link = f"https://drive.google.com/file/d/{file_id}/view"
        try:
            os.remove(pdf_path)
        except:
            pass

        # ================= SAVE TO SHEETS =================
        
        save_to_sheets_structured(request.form, drive_link, signature_url,emp_id)

        print("PDF folder:", pdf_folder_id)
        print("Signature folder:", signature_folder_id)

        return jsonify({
            "status": "success",
            "pdf": pdf_filename
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/download_pdf/<filename>")
def download_pdf(filename):
    return send_file(os.path.join(PDF_FOLDER, filename), as_attachment=True)


@app.route("/success")
def success():
    return render_template("success.html")


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)