from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from mysql.connector import Error, IntegrityError
from pathlib import Path
from datetime import datetime
import tempfile
import re
import logging

from database import get_db
from services.resume_parser import extract_pdf_text
from services.matching import calculate_match


# ==================================================
# 1. FLASK CONFIGURATION
# ==================================================

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_FOLDER = BASE_DIR / "uploads" / "resumes"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 55 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf"}
MAX_RESUME_SIZE = 5 * 1024 * 1024
MAX_BULK_FILES = 10
MAX_TOTAL_RESUMES = 100

logging.basicConfig(level=logging.INFO)


# ==================================================
# 2. COMMON HELPERS
# ==================================================

def error(message, status_code=400):
    return jsonify({
        "success": False,
        "message": message
    }), status_code


def close_db(connection=None, cursor=None):
    try:
        if cursor:
            cursor.close()
    except Exception:
        app.logger.exception("Cursor closing error")

    try:
        if connection and connection.is_connected():
            connection.close()
    except Exception:
        app.logger.exception("Database closing error")


def json_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def clean_job(job):
    if not job:
        return None

    return {
        "id": job.get("id"),
        "recruiter_id": job.get("recruiter_id"),
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "required_skills": job.get("required_skills"),
        "description": job.get("description"),
        "status": job.get("status"),
        "created_at": json_value(job.get("created_at"))
    }


def valid_user(cursor, user_id, role):
    cursor.execute(
        """
        SELECT id, name, email, role
        FROM users
        WHERE id = %s AND role = %s
        """,
        (user_id, role)
    )
    return cursor.fetchone()


def get_candidate_resume(cursor, candidate_id):
    cursor.execute(
        """
        SELECT extracted_text
        FROM resumes
        WHERE candidate_id = %s
        ORDER BY uploaded_at DESC
        LIMIT 1
        """,
        (candidate_id,)
    )

    result = cursor.fetchone()

    return (
        result.get("extracted_text") or ""
        if result else ""
    )


def get_screening_status(score):
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0

    if score >= 70:
        return "Strong Match"
    elif score >= 40:
        return "Moderate Match"
    return "Low Match"


# ==================================================
# 3. HOME AND HEALTH CHECK
# ==================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "success": True,
        "message": "Welcome to HireLens API"
    })


@app.route("/api/health", methods=["GET"])
def health():
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()

        return jsonify({
            "success": True,
            "message": "HireLens backend and database are working"
        })

    except Error:
        app.logger.exception("Database connection error")
        return error("Database connection failed.", 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 4. USER REGISTRATION
# ==================================================

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "").strip().lower()

    if not name or not email or not password or not role:
        return error("Please fill all required fields.")

    if role not in ["candidate", "recruiter"]:
        return error("Role must be candidate or recruiter.")

    if len(password) < 6:
        return error("Password must contain at least 6 characters.")

    password_hash = generate_password_hash(password)

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            INSERT INTO users
            (name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            """,
            (name, email, password_hash, role)
        )

        user_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "success": True,
            "message": "Registration successful",
            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "role": role
            }
        }), 201

    except IntegrityError:
        if connection:
            connection.rollback()
        return error("This email is already registered.", 409)

    except Error as e:
        if connection:
            connection.rollback()
        app.logger.exception("Registration error")
        return error(str(e), 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 5. USER LOGIN
# ==================================================

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return error("Email and password are required.")

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, email, password_hash, role
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        if not user or not check_password_hash(
            user["password_hash"], password
        ):
            return error("Invalid email or password.", 401)

        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"]
            }
        })

    except Error as e:
        app.logger.exception("Login error")
        return error(str(e), 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 6. GET ALL PUBLISHED JOBS
# ==================================================

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM jobs
            WHERE status = 'Published'
            ORDER BY created_at DESC
            """
        )

        jobs = cursor.fetchall()

        return jsonify({
            "success": True,
            "jobs": [clean_job(job) for job in jobs]
        })

    except Error as e:
        return error(str(e), 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 7. CREATE JOB
# ==================================================

@app.route("/api/jobs", methods=["POST"])
def create_job():
    data = request.get_json(silent=True) or {}

    recruiter_id = data.get("recruiter_id")
    title = (data.get("title") or "").strip()
    company = (data.get("company") or "").strip()
    location = (data.get("location") or "").strip()
    required_skills = data.get("required_skills") or ""
    description = data.get("description") or ""
    status = data.get("status") or "Published"

    if not recruiter_id or not title:
        return error("Recruiter ID and job title are required.")

    if status not in ["Draft", "Published", "Closed", "Active", "Inactive"]:
    return error("Invalid job status.")

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        recruiter = valid_user(cursor, recruiter_id, "recruiter")

        if not recruiter:
            return error("Recruiter account not found.", 404)

        cursor.execute(
            """
            INSERT INTO jobs
            (
                recruiter_id,
                title,
                company,
                location,
                required_skills,
                description,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                recruiter_id,
                title,
                company,
                location,
                required_skills,
                description,
                status
            )
        )

        job_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "success": True,
            "message": "Job created successfully",
            "job_id": job_id
        }), 201

    except Error as e:
        if connection:
            connection.rollback()
        return error(str(e), 500)

    finally:
        close_db(connection, cursor)
        # ==================================================
# 8. GET RECRUITER JOBS
# ==================================================

@app.route(
    "/api/recruiter/<int:recruiter_id>/jobs",
    methods=["GET"]
)
def recruiter_jobs(recruiter_id):

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        recruiter = valid_user(
            cursor, recruiter_id, "recruiter"
        )

        if not recruiter:
            return error("Recruiter not found.", 404)

        cursor.execute(
            """
            SELECT *
            FROM jobs
            WHERE recruiter_id = %s
            ORDER BY created_at DESC
            """,
            (recruiter_id,)
        )

        jobs = cursor.fetchall()

        return jsonify({
            "success": True,
            "jobs": [clean_job(job) for job in jobs]
        })

    except Error as e:
        return error(str(e), 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 9. UPDATE JOB
# ==================================================

@app.route("/api/jobs/<int:job_id>", methods=["PUT"])
def update_job(job_id):

    data = request.get_json(silent=True) or {}

    recruiter_id = data.get("recruiter_id")
    title = (data.get("title") or "").strip()

    if not recruiter_id or not title:
        return error(
            "Recruiter ID and title are required."
        )

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id
            FROM jobs
            WHERE id = %s AND recruiter_id = %s
            """,
            (job_id, recruiter_id)
        )

        if not cursor.fetchone():
            return error(
                "Job not found or access denied.",
                404
            )

        cursor.execute(
            """
            UPDATE jobs
            SET title = %s,
                company = %s,
                location = %s,
                required_skills = %s,
                description = %s
            WHERE id = %s AND recruiter_id = %s
            """,
            (
                title,
                data.get("company", ""),
                data.get("location", ""),
                data.get("required_skills", ""),
                data.get("description", ""),
                job_id,
                recruiter_id
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Job updated successfully"
        })

    except Error as e:

        if connection:
            connection.rollback()

        return error(str(e), 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 10. UPDATE JOB STATUS
# ==================================================

@app.route(
    "/api/jobs/<int:job_id>/status",
    methods=["PATCH"]
)
def update_job_status(job_id):

    data = request.get_json(silent=True) or {}

    recruiter_id = data.get("recruiter_id")
    status = data.get("status")

    if (
        not recruiter_id
        or status not in ["Draft", "Published", "Closed"]
    ):
        return error(
            "Valid recruiter ID and status are required."
        )

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            UPDATE jobs
            SET status = %s
            WHERE id = %s AND recruiter_id = %s
            """,
            (status, job_id, recruiter_id)
        )

        if cursor.rowcount == 0:

            cursor.execute(
                """
                SELECT id
                FROM jobs
                WHERE id = %s AND recruiter_id = %s
                """,
                (job_id, recruiter_id)
            )

            if not cursor.fetchone():
                return error(
                    "Job not found or access denied.",
                    404
                )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Job status updated successfully"
        })

    except Error as e:

        if connection:
            connection.rollback()

        return error(str(e), 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 11. GET CANDIDATE PROFILE
# ==================================================

@app.route(
    "/api/candidate/<int:candidate_id>/profile",
    methods=["GET"]
)
def get_candidate_profile(candidate_id):

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        candidate = valid_user(
            cursor, candidate_id, "candidate"
        )

        if not candidate:
            return error("Candidate not found.", 404)

        cursor.execute(
            """
            SELECT *
            FROM candidate_profiles
            WHERE candidate_id = %s
            """,
            (candidate_id,)
        )

        profile = cursor.fetchone()

        if profile and profile.get("updated_at"):
            profile["updated_at"] = json_value(
                profile["updated_at"]
            )

        return jsonify({
            "success": True,
            "user": candidate,
            "profile": profile
        })

    except Error as e:

        return error(str(e), 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 12. CREATE OR UPDATE CANDIDATE PROFILE
# ==================================================

@app.route(
    "/api/candidate/<int:candidate_id>/profile",
    methods=["PUT"]
)
def update_candidate_profile(candidate_id):

    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or "").strip()
    phone = data.get("phone", "")
    education = data.get("education", "")
    location = data.get("location", "")
    skills = data.get("skills", "")
    about = data.get("about", "")

    if not full_name:
        return error("Full name is required.")

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        candidate = valid_user(
            cursor, candidate_id, "candidate"
        )

        if not candidate:
            return error("Candidate not found.", 404)

        cursor.execute(
            """
            INSERT INTO candidate_profiles
            (
                candidate_id,
                full_name,
                phone,
                education,
                location,
                skills,
                about
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)

            ON DUPLICATE KEY UPDATE
                full_name = VALUES(full_name),
                phone = VALUES(phone),
                education = VALUES(education),
                location = VALUES(location),
                skills = VALUES(skills),
                about = VALUES(about),
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                candidate_id,
                full_name,
                phone,
                education,
                location,
                skills,
                about
            )
        )

        cursor.execute(
            """
            UPDATE users
            SET name = %s
            WHERE id = %s
            """,
            (full_name, candidate_id)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Candidate profile saved successfully"
        })

    except Error as e:

        if connection:
            connection.rollback()

        return error(str(e), 500)

    finally:
        close_db(connection, cursor)
       
# ==================================================
# 13. UPLOAD CANDIDATE RESUME
# ==================================================

@app.route(
    "/api/candidate/<int:candidate_id>/resume",
    methods=["POST"]
)
def upload_resume(candidate_id):

    if "resume" not in request.files:
        return error("Please select a resume PDF.")

    file = request.files["resume"]

    if not file.filename:
        return error("No file selected.")

    if not file.filename.lower().endswith(".pdf"):
        return error("Only PDF files are allowed.")

    connection = None
    cursor = None
    saved_path = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        candidate = valid_user(
            cursor, candidate_id, "candidate"
        )

        if not candidate:
            return error("Candidate not found.", 404)

        safe_name = secure_filename(file.filename)

        if not safe_name:
            return error("Invalid filename.")

        unique_name = (
            f"{candidate_id}_"
            f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_"
            f"{safe_name}"
        )

        saved_path = UPLOAD_FOLDER / unique_name

        file.save(str(saved_path))

        # Check file size (maximum 5 MB)
        if saved_path.stat().st_size > MAX_RESUME_SIZE:
            saved_path.unlink(missing_ok=True)
            return error("Resume file cannot exceed 5 MB.")

        # Extract text from PDF
        extracted_text = extract_pdf_text(saved_path)

        if not extracted_text or not extracted_text.strip():
            saved_path.unlink(missing_ok=True)
            return error(
                "No selectable text found in this PDF."
            )

        # Save resume details in MySQL database
        cursor.execute(
            """
            INSERT INTO resumes
            (candidate_id, filename, path, extracted_text)
            VALUES (%s, %s, %s, %s)
            """,
            (
                candidate_id,
                safe_name,
                str(saved_path),
                extracted_text
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Resume uploaded successfully",
            "filename": safe_name
        }), 201

    except Error as e:

        if connection:
            connection.rollback()

        if saved_path and saved_path.exists():
            saved_path.unlink()

        app.logger.exception("Resume database error")

        return error(str(e), 500)

    except Exception as e:

        if connection:
            connection.rollback()

        if saved_path and saved_path.exists():
            saved_path.unlink()

        app.logger.exception("Resume processing failed")

        return error(
            f"Unable to process this PDF: {str(e)}",
            400
        )

    finally:
        close_db(connection, cursor)



# 14. AI JOB MATCHING
# ==================================================

@app.route(
    "/api/candidate/<int:candidate_id>/matches",
    methods=["GET"]
)
def candidate_matches(candidate_id):

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        candidate = valid_user(
            cursor, candidate_id, "candidate"
        )

        if not candidate:
            return error("Candidate not found.", 404)

        cursor.execute(
            """
            SELECT *
            FROM candidate_profiles
            WHERE candidate_id = %s
            """,
            (candidate_id,)
        )

        profile = cursor.fetchone() or {}

        resume_text = get_candidate_resume(
            cursor, candidate_id
        )

        candidate_text = " ".join([
            str(profile.get("skills") or ""),
            str(profile.get("education") or ""),
            str(profile.get("about") or ""),
            resume_text
        ])

        if not candidate_text.strip():
            return error(
                "Please complete your profile or upload a resume first."
            )

        cursor.execute(
            """
            SELECT *
            FROM jobs
            WHERE status = 'Published'
            """
        )

        jobs = cursor.fetchall()

        matches = []

        for job in jobs:

            score, matched, missing = calculate_match(
                candidate_text, job
            )

            matches.append({
                "job": clean_job(job),
                "match_score": score,
                "matched_skills": matched,
                "missing_skills": missing
            })

        matches.sort(
            key=lambda item: item["match_score"],
            reverse=True
        )

        return jsonify({
            "success": True,
            "matches": matches
        })

    except Error as e:

        return error(str(e), 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 15. APPLY FOR A JOB
# ==================================================

@app.route("/api/applications", methods=["POST"])
def apply_job():

    data = request.get_json(silent=True) or {}

    candidate_id = data.get("candidate_id")
    job_id = data.get("job_id")

    if not candidate_id or not job_id:
        return error(
            "Candidate ID and Job ID are required."
        )

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        candidate = valid_user(
            cursor, candidate_id, "candidate"
        )

        if not candidate:
            return error("Candidate not found.", 404)

        cursor.execute(
            """
            SELECT *
            FROM jobs
            WHERE id = %s AND status = 'Published'
            """,
            (job_id,)
        )

        job = cursor.fetchone()

        if not job:
            return error("Job is not available.", 404)

        cursor.execute(
            """
            SELECT *
            FROM candidate_profiles
            WHERE candidate_id = %s
            """,
            (candidate_id,)
        )

        profile = cursor.fetchone() or {}

        resume_text = get_candidate_resume(
            cursor, candidate_id
        )

        if not resume_text or not resume_text.strip():
            return error(
                "Please upload your PDF resume from My Profile before applying.",
                400
            )

        candidate_text = " ".join([
            str(profile.get("skills") or ""),
            str(profile.get("education") or ""),
            str(profile.get("about") or ""),
            resume_text
        ])

        score, matched, missing = calculate_match(
            candidate_text, job
        )

        cursor.execute(
            """
            INSERT INTO applications
            (job_id, candidate_id, match_score, status)
            VALUES (%s, %s, %s, 'Pending')
            """,
            (job_id, candidate_id, score)
        )

        application_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Application submitted successfully",
            "application_id": application_id,
            "match_score": score,
            "matched_skills": matched,
            "missing_skills": missing
        }), 201

    except IntegrityError:

        if connection:
            connection.rollback()

        return error(
            "You have already applied for this job.",
            409
        )

    except Error as e:

        if connection:
            connection.rollback()

        return error(str(e), 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 16. CANDIDATE APPLICATIONS
# ==================================================

@app.route(
    "/api/candidate/<int:candidate_id>/applications",
    methods=["GET"]
)
def candidate_applications(candidate_id):

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        candidate = valid_user(
            cursor, candidate_id, "candidate"
        )

        if not candidate:
            return error("Candidate not found.", 404)

        cursor.execute(
            """
            SELECT
                a.id AS application_id,
                a.job_id,
                a.candidate_id,
                a.match_score,
                a.status AS application_status,
                a.applied_at,
                j.title,
                j.company,
                j.location
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE a.candidate_id = %s
            ORDER BY a.applied_at DESC
            """,
            (candidate_id,)
        )

        applications = cursor.fetchall()

        for application in applications:
            application["applied_at"] = json_value(
                application.get("applied_at")
            )

        return jsonify({
            "success": True,
            "applications": applications
        })

    except Error as e:
        return error(str(e), 500)

    finally:
        close_db(connection, cursor)
        # ==================================================
# 17. RECRUITER APPLICATIONS
# ==================================================

@app.route(
    "/api/recruiter/<int:recruiter_id>/applications",
    methods=["GET"]
)
def recruiter_applications(recruiter_id):

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        recruiter = valid_user(
            cursor, recruiter_id, "recruiter"
        )

        if not recruiter:
            return error("Recruiter not found.", 404)

        cursor.execute(
            """
            SELECT
                a.id AS application_id,
                a.job_id,
                a.candidate_id,
                a.match_score,
                a.status,
                a.applied_at,
                u.name AS candidate_name,
                u.email AS candidate_email,
                j.title AS job_title
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            JOIN users u ON a.candidate_id = u.id
            WHERE j.recruiter_id = %s
            ORDER BY a.applied_at DESC
            """,
            (recruiter_id,)
        )

        applications = cursor.fetchall()

        for application in applications:
            application["applied_at"] = json_value(
                application.get("applied_at")
            )

        return jsonify({
            "success": True,
            "applications": applications
        })

    except Error as e:
        return error(str(e), 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 18. UPDATE APPLICATION STATUS
# ==================================================

@app.route(
    "/api/applications/<int:application_id>/status",
    methods=["PATCH"]
)
def update_application_status(application_id):

    data = request.get_json(silent=True) or {}

    recruiter_id = data.get("recruiter_id")
    status = data.get("status")

    allowed_statuses = [
        "Pending",
        "Shortlisted",
        "Interview",
        "Rejected",
        "Hired"
    ]

    if (
        not recruiter_id
        or status not in allowed_statuses
    ):
        return error(
            "Valid recruiter ID and application status are required."
        )

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT a.id
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE a.id = %s AND j.recruiter_id = %s
            """,
            (application_id, recruiter_id)
        )

        if not cursor.fetchone():
            return error(
                "Application not found or access denied.",
                404
            )

        cursor.execute(
            """
            UPDATE applications
            SET status = %s
            WHERE id = %s
            """,
            (status, application_id)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Application status updated successfully"
        })

    except Error as e:

        if connection:
            connection.rollback()

        return error(str(e), 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 19. RECRUITER DASHBOARD STATISTICS
# ==================================================

@app.route(
    "/api/recruiter/<int:recruiter_id>/stats",
    methods=["GET"]
)
def recruiter_stats(recruiter_id):

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        recruiter = valid_user(
            cursor, recruiter_id, "recruiter"
        )

        if not recruiter:
            return error("Recruiter not found.", 404)

        cursor.execute(
            """
            SELECT COUNT(*) AS total_jobs
            FROM jobs
            WHERE recruiter_id = %s
            """,
            (recruiter_id,)
        )

        total_jobs = cursor.fetchone()["total_jobs"]

        cursor.execute(
            """
            SELECT COUNT(*) AS active_jobs
            FROM jobs
            WHERE recruiter_id = %s
            AND status = 'Published'
            """,
            (recruiter_id,)
        )

        active_jobs = cursor.fetchone()["active_jobs"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total_applications
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE j.recruiter_id = %s
            """,
            (recruiter_id,)
        )

        total_applications = cursor.fetchone()["total_applications"]

        cursor.execute(
            """
            SELECT COUNT(*) AS shortlisted
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE j.recruiter_id = %s
            AND a.status = 'Shortlisted'
            """,
            (recruiter_id,)
        )

        shortlisted = cursor.fetchone()["shortlisted"]

        return jsonify({
            "success": True,
            "stats": {
                "total_jobs": int(total_jobs),
                "active_jobs": int(active_jobs),
                "total_applications": int(total_applications),
                "shortlisted": int(shortlisted)
            }
        })

    except Error as e:
        return error(str(e), 500)

    finally:
        close_db(connection, cursor)


# ==================================================
# 20. RANKED CANDIDATES
# ==================================================

@app.route(
    "/api/recruiter/<int:recruiter_id>/jobs/<int:job_id>/candidates",
    methods=["GET"]
)
def ranked_candidates(recruiter_id, job_id):

    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        recruiter = valid_user(
            cursor, recruiter_id, "recruiter"
        )

        if not recruiter:
            return error("Recruiter not found.", 404)

        cursor.execute(
            """
            SELECT *
            FROM jobs
            WHERE id = %s AND recruiter_id = %s
            """,
            (job_id, recruiter_id)
        )

        job = cursor.fetchone()

        if not job:
            return error(
                "Job not found or access denied.",
                404
            )

        cursor.execute(
            """
            SELECT
                a.id AS application_id,
                a.candidate_id,
                a.status,
                a.match_score AS application_match_score,
                u.name,
                u.email,
                cp.skills,
                cp.education,
                cp.location,
                cp.about
            FROM applications a
            JOIN users u ON a.candidate_id = u.id
            LEFT JOIN candidate_profiles cp
                ON a.candidate_id = cp.candidate_id
            WHERE a.job_id = %s
            """,
            (job_id,)
        )

        applicants = cursor.fetchall()

        ranked = []

        for applicant in applicants:

            resume_text = get_candidate_resume(
                cursor,
                applicant["candidate_id"]
            )

            candidate_text = " ".join([
                str(applicant.get("skills") or ""),
                str(applicant.get("education") or ""),
                str(applicant.get("about") or ""),
                resume_text
            ])

            score, matched, missing = calculate_match(
                candidate_text,
                job
            )

            ranked.append({
                "application_id": applicant["application_id"],
                "candidate_id": applicant["candidate_id"],
                "name": applicant["name"],
                "email": applicant["email"],
                "skills": applicant.get("skills"),
                "education": applicant.get("education"),
                "location": applicant.get("location"),
                "application_status": applicant["status"],
                "match_score": score,
                "matched_skills": matched,
                "missing_skills": missing
            })

        ranked.sort(
            key=lambda item: item["match_score"],
            reverse=True
        )

        return jsonify({
            "success": True,
            "candidates": ranked
        })

    except Error as e:
        return error(str(e), 500)

    finally:
        close_db(connection, cursor)
        # ==================================================
# 21. BULK AI RESUME SCREENING
# ==================================================

@app.route(
    "/api/recruiter/<int:recruiter_id>/jobs/<int:job_id>/screen-resumes",
    methods=["POST"]
)
def bulk_screen_resumes(recruiter_id, job_id):

    files = request.files.getlist("resumes")

    if not files:
        return error(
            "Please select at least one PDF resume."
        )

    if len(files) > MAX_BULK_FILES:
        return error(
            "Maximum 10 PDF resumes allowed per batch."
        )

    connection = None
    cursor = None

    results = []
    failed_files = []

    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)

        # Verify recruiter
        recruiter = valid_user(
            cursor,
            recruiter_id,
            "recruiter"
        )

        if not recruiter:
            return error("Recruiter not found.", 404)

        # Verify job ownership
        cursor.execute(
            """
            SELECT *
            FROM jobs
            WHERE id = %s AND recruiter_id = %s
            """,
            (job_id, recruiter_id)
        )

        job = cursor.fetchone()

        if not job:
            return error(
                "Job not found or access denied.",
                404
            )

        app.logger.info(
            "Bulk screening started: %s files",
            len(files)
        )

        for index, file in enumerate(files, start=1):

            original_name = (
                file.filename or f"Resume_{index}.pdf"
            )

            safe_name = secure_filename(original_name)
            temp_path = None

            try:
                # Check PDF extension
                if (
                    not safe_name
                    or not safe_name.lower().endswith(".pdf")
                ):
                    raise ValueError(
                        "Only PDF files are supported."
                    )

                # Read maximum allowed size + 1 byte
                file_bytes = file.stream.read(
                    MAX_RESUME_SIZE + 1
                )

                if not file_bytes:
                    raise ValueError("File is empty.")

                if len(file_bytes) > MAX_RESUME_SIZE:
                    raise ValueError("PDF exceeds 5 MB.")

                # Basic PDF signature check
                if not file_bytes.startswith(b"%PDF"):
                    raise ValueError("Invalid PDF file.")

                # Save temporary PDF
                with tempfile.NamedTemporaryFile(
                    suffix=".pdf",
                    dir=str(UPLOAD_FOLDER),
                    delete=False
                ) as temp_file:

                    temp_file.write(file_bytes)
                    temp_path = Path(temp_file.name)

                # Extract text
                resume_text = extract_pdf_text(temp_path)

                if not resume_text or not resume_text.strip():
                    raise ValueError(
                        "No selectable text found. "
                        "Scanned PDFs are not supported."
                    )

                # Match resume with selected job
                score, matched, missing = calculate_match(
                    resume_text,
                    job
                )

                # Extract email
                email_match = re.search(
                    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                    resume_text
                )

                results.append({
                    "filename": safe_name,
                    "candidate_name": Path(safe_name).stem,
                    "email": (
                        email_match.group(0)
                        if email_match
                        else "Not found"
                    ),
                    "match_score": score,
                    "matched_skills": matched,
                    "missing_skills": missing,
                    "screening_status": get_screening_status(score)
                })

                app.logger.info(
                    "Screened %s/%s: %s",
                    index,
                    len(files),
                    safe_name
                )

            except Exception as file_error:

                app.logger.exception(
                    "Failed resume: %s",
                    safe_name
                )

                failed_files.append({
                    "filename": safe_name or original_name,
                    "message": str(file_error)
                })

            finally:
                # Delete temporary file
                if temp_path and temp_path.exists():
                    try:
                        temp_path.unlink()
                    except OSError:
                        app.logger.warning(
                            "Could not delete temporary file: %s",
                            temp_path
                        )

        # Sort highest score first
        results.sort(
            key=lambda item: item["match_score"],
            reverse=True
        )

        app.logger.info(
            "Batch completed. Successful: %s, Failed: %s",
            len(results),
            len(failed_files)
        )

        return jsonify({
            "success": True,
            "message": "Batch screening completed.",
            "job_title": job.get("title"),
            "total_uploaded": len(files),
            "successfully_screened": len(results),
            "failed_count": len(failed_files),
            "results": results,
            "failed_files": failed_files
        })

    except Exception:
        app.logger.exception("Bulk screening API error")

        return error(
            "Screening failed due to a server error.",
            500
        )

    finally:
        close_db(connection, cursor)


# ==================================================
# 22. FILE SIZE ERROR
# ==================================================

@app.errorhandler(413)
def file_too_large(e):

    return error(
        "Batch upload exceeded 55 MB. "
        "Please upload smaller PDF files.",
        413
    )


# ==================================================
# 23. START SERVER
# ==================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
