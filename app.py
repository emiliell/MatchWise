import spacy
from pymongo import MongoClient
from gridfs import GridFS
from flask import send_file
from bson import ObjectId
from flask import Flask, request, render_template, redirect, url_for, flash
from flask import abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from flask_bcrypt import Bcrypt
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Email
from dotenv import load_dotenv
import os
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from io import BytesIO
from pdfminer.high_level import extract_text
from sentence_transformers import SentenceTransformer, util
import math
from datetime import datetime, timezone



load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'random_key'

bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)


# ===========================================================================================================
# Utility: NLP & Scoring
# ===========================================================================================================
def extract_tech(nlp, text: str) -> set[str]:
    doc = nlp(text or "")
    tech = []
    for ent in doc.ents:
        if ent.label_ in ["ORG", "TECHNOLOGY", "TECH"]:
            tech.append(ent.text)
    return {t.strip().lower() for t in set(tech) if t.strip()}

def extract_pdf_text(file_storage) -> str:
    data = file_storage.read()
    file_storage.stream.seek(0)
    return extract_text(BytesIO(data)) or ""

# ===========================================================================================================
# Semantic model
# ===========================================================================================================
_sem_model = None
def get_sem_model():
    global _sem_model
    if _sem_model is None:
        _sem_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sem_model

def coverage(jd_tech: set[str], resume_skills: set[str]) -> float:
    """Fraction of JD skills covered by the resume (0..1)."""
    if not jd_tech:
        return 0.0
    return len(jd_tech & resume_skills) / len(jd_tech)

def combined_similarity(jd_text: str, jd_tech: set[str],
                        resume_text: str, resume_skills: set[str]) -> tuple[float, float]:
    """
    Returns (similarity_score_0_100, success_rate_0_100)
    - similarity blends semantic doc similarity (65%) + JD skill coverage (35%)
    - success is a calibrated sigmoid of the same signals (probability-like)
    """
    # 1) semantic similarity (0..1)
    try:
        model = get_sem_model()
        jd_emb = model.encode(jd_text or "", normalize_embeddings=True)
        rs_emb = model.encode(resume_text or "", normalize_embeddings=True)
        sem = float(util.cos_sim(jd_emb, rs_emb))
        sem = max(0.0, min(1.0, sem))
    except Exception:
        sem = 0.0

    # 2) skill coverage (0..1)
    cov = coverage(jd_tech, resume_skills)

    # 3) blended similarity (0..100)
    sim = 100.0 * (0.65 * sem + 0.35 * cov)

    # 4) success via logistic calibration (0..100)
    z = 0.7 * sem + 0.3 * cov   # emphasise semantics slightly
    success = 100.0 / (1.0 + math.exp(-4.0 * (z - 0.55)))
    if cov == 0:
        success = min(success, 15.0)

    return round(sim, 1), round(success, 1)



# ===========================================================================================================
# Auth: Models & Forms
# ===========================================================================================================
class User(UserMixin):
    def __init__(self, email, user_type):
        self.id = email
        self.user_type = user_type

@login_manager.user_loader
def load_user(email):
    client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True) # Replace this with your own MongoDB url
    db = client["login"]
    user_data = db.users.find_one({"email": email})
    if user_data:
        return User(email=user_data["email"], user_type=user_data["user_type"])

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    user_type = StringField('User Type (candidate or company)', validators=[DataRequired()])
    submit = SubmitField('Register')




# ===========================================================================================================
# Routes: Auth
# ===========================================================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
        db = client["login"]
        user = db.users.find_one({"email": form.email.data})
        matched = bcrypt.check_password_hash(user['password'], form.password.data)
        
        if user and matched:
            user_obj = User(email=user["email"], user_type=user["user_type"])
            login_user(user_obj)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)



@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = {
            "email": form.email.data,
            "password": hashed_password,
            "user_type": form.user_type.data.lower()
        }

        # Insert the new user data into database
        client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
        db = client["login"]
        db.users.insert_one(new_user)

        print("CREATED")
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/logout", methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))



# ===========================================================================================================
# Routes: Navigation / Landing
# ===========================================================================================================
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_authenticated:
        flash('Please log in to access this page.')
    
    if current_user.user_type == 'candidate':
        return redirect(url_for('upload_form'))
    elif current_user.user_type == 'company':
        return render_template('job_desc.html')
    else:
        flash('Unauthorized user type', 'danger')
        return redirect(url_for('logout'))


@app.route('/upload_form')
@login_required
def upload_form():
    if current_user.user_type != 'candidate':
        flash('You do not have access to this page', 'danger')
        return redirect('job_desc.html')
    return render_template('upload.html')



# ===========================================================================================================
# Routes: Candidate – Upload, Compare, History
# ===========================================================================================================
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "GET":
        return render_template("upload.html")

    # Use the authenticated user
    email = current_user.id
    name = current_user.id.split("@")[0].title()

    resume_file = request.files.get("resume")
    if not resume_file:
        flash("Please choose a PDF to upload.", "warning")
        return render_template("upload.html")

    # 1) Read PDF text
    try:
        pdf_text = extract_pdf_text(resume_file)
    except Exception as e:
        flash("Could not read that PDF. Please upload a text-based PDF.", "danger")
        return render_template("upload.html")

    # 2) Load spaCy
    try:
        nlp = spacy.load("model_upgrade")
    except Exception:
        nlp = spacy.load("en_core_web_sm")

    # 3) Auto-extract skills from PDF text
    skills = sorted(list(extract_tech(nlp, pdf_text)))

    # 4) Save file to GridFS + record to Mongo
    client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
    db = client["candidates"]
    fs = GridFS(db)

    resume_id = fs.put(resume_file, filename=resume_file.filename)

    users = db["candidates"]
    users.insert_one({
        "name": name,
        "email": email,
        "skills": skills,
        "resume_id": resume_id,
        "resume_filename": resume_file.filename,
        "resume_text": (pdf_text or "")[:50000]
    })

    flash("Resume uploaded and skills extracted automatically.", "success")
    return redirect(url_for("upload"))


@app.route('/candidate/compare', methods=['GET', 'POST'])
@login_required
def candidate_compare():
    if current_user.user_type != 'candidate':
        abort(403)

    # Load spaCy
    try:
        nlp = spacy.load("model_upgrade")
    except Exception:
        nlp = spacy.load("en_core_web_sm")

    # Fetch only this user's resumes for the dropdown
    client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
    db = client["candidates"]
    users = db["candidates"]

    my_docs = list(users.find({"email": current_user.id}))
    options = []
    for d in my_docs:
        rid = str(d.get("resume_id"))
        label = d.get("resume_filename") or f"{d.get('name','Resume')} • {rid[:6]}…"
        options.append({"id": rid, "label": label})

    if request.method == 'POST':
            jd_text = request.form.get('job_description', '').strip()
            chosen = request.form.get('resume_id', '').strip()

            if not jd_text:
                flash('Please paste a job description.', 'warning')
                return render_template('candidate_compare.html', options=options)

            if not chosen:
                flash('Please select one of your resumes.', 'warning')
                return render_template('candidate_compare.html', options=options, jd_text=jd_text)

            # Fetch the selected resume
            try:
                rid_obj = ObjectId(chosen)
            except Exception:
                flash('Invalid resume selection.', 'danger')
                return render_template('candidate_compare.html', options=options, jd_text=jd_text)

            doc = users.find_one({"email": current_user.id, "resume_id": rid_obj})
            if not doc:
                flash('That resume was not found in your account.', 'danger')
                return render_template('candidate_compare.html', options=options, jd_text=jd_text)

            # lowercased sets + semantic + coverage
            jd_tech = {s.lower() for s in extract_tech(nlp, jd_text)}
            res_skills = {s.lower() for s in (doc.get('skills') or [])}

            # resume_text (fallback to GridFS if missing)
            resume_text = (doc.get("resume_text") or "").strip()
            if not resume_text:
                try:
                    fs = GridFS(client["candidates"])
                    fobj = fs.get(doc["resume_id"])
                    pdf_bytes = fobj.read()
                    fobj.close()
                    resume_text = extract_text(BytesIO(pdf_bytes)) or ""
                except Exception:
                    resume_text = ""

            similarity_score, success_rate = combined_similarity(
                jd_text, jd_tech, resume_text, res_skills
            )

            result = {
                "name": doc.get("name"),
                "email": doc.get("email"),
                "resume_id": str(doc.get("resume_id")),
                "resume_filename": doc.get("resume_filename"),
                "score": similarity_score,      # uses new blend
                "success_rate": success_rate,   # probability-like
                "matched": sorted(list(jd_tech & res_skills)),
            }

            # Save compare history
            history = {
                "email": current_user.id,
                "resume_id": doc.get("resume_id"),
                "resume_filename": doc.get("resume_filename"),
                "jd_text": jd_text[:4000],
                "jd_tech": sorted(list(jd_tech)),
                "matched_skills": result["matched"],
                "similarity_score": similarity_score,
                "success_rate": success_rate,
                "compared_at": datetime.now(timezone.utc)  # store as UTC datetime
            }
            db["compare_history"].insert_one(history)


            return render_template(
                "candidate_compare.html",
                options=options,
                jd_text=jd_text,
                jd_tech=sorted(list(jd_tech)),
                result=result,
            )
    # GET
    return render_template('candidate_compare.html', options=options)


@app.route('/candidate/history')
@login_required
def candidate_history():
    if current_user.user_type != 'candidate':
        abort(403)

    client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
    db = client["candidates"]

    records = list(
        db["compare_history"]
        .find({"email": current_user.id})
        .sort("compared_at", -1)
    )

    # normalise for template
    for r in records:
        r["_id"] = str(r.get("_id"))
        rid = r.get("resume_id")
        r["resume_id_str"] = str(rid) if rid else None
        # short preview for the JD
        jdt = (r.get("jd_text") or "").strip()
        r["jd_preview"] = (jdt[:140] + "…") if len(jdt) > 140 else jdt

    return render_template("candidate_history.html", records=records)


@app.route('/candidate/history/clear', methods=['POST'])
@login_required
def clear_candidate_history():
    if current_user.user_type != 'candidate':
        abort(403)

    client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
    db = client["candidates"]

    db["compare_history"].delete_many({"email": current_user.id})

    flash("Your comparison history has been cleared.", "success")
    return redirect(url_for('candidate_history'))






# ===========================================================================================================
# Routes: Company – Match & History
# ===========================================================================================================
@app.route('/match', methods=['GET', 'POST'])
@login_required
def match():
    if request.method == 'POST':
        job_description = (request.form.get('job_description') or "").strip()
        if not job_description:
            flash("Please paste a job description.", "warning")
            return render_template('job_desc.html')

        # Load spaCy
        try:
            nlp = spacy.load("model_upgrade")
        except Exception:
            nlp = spacy.load("en_core_web_sm")

        # Extract JD technologies (set of lowercased strings)
        jd_tech = {s.lower() for s in extract_tech(nlp, job_description)}

        client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
        db = client["candidates"]
        users_col = db["candidates"]
        fs = GridFS(db)

        matched_resumes = []
        for user in users_col.find({}):
            resume_skills = {s.lower() for s in (user.get("skills") or [])}

            # Get stored resume text (fallback to GridFS read if missing)
            resume_text = (user.get("resume_text") or "").strip()
            if not resume_text:
                try:
                    fobj = fs.get(user["resume_id"])
                    pdf_bytes = fobj.read()
                    fobj.close()
                    resume_text = extract_text(BytesIO(pdf_bytes)) or ""
                except Exception:
                    resume_text = ""

            # Compute blended scores
            similarity_score, success_rate = combined_similarity(
                job_description,
                jd_tech,
                resume_text,
                resume_skills
            )

            matched_resumes.append({
                "candidate_name": user.get("name", "Unknown"),
                "match_score": similarity_score,
                "success_rate": success_rate,
                "job": {
                    "description": job_description,
                    "skills": sorted(list(jd_tech)),
                },
                "resume_url": url_for('fetch_resume', resume_id=str(user.get("resume_id"))),
            })

        # Sort by success then similarity
        matched_resumes = sorted(
            matched_resumes,
            key=lambda r: (r["success_rate"], r["match_score"]),
            reverse=True
        )

        # Keep only the essentials + limit top 20 to keep docs small
        history_results = []
        for r in matched_resumes[:20]:
            history_results.append({
                "candidate_name": r.get("candidate_name"),
                "resume_id": r.get("resume_url").rsplit("/", 1)[-1] if r.get("resume_url") else None,
                "resume_filename": None,
                "match_score": r.get("match_score"),
                "success_rate": r.get("success_rate"),
                "jd_skills": r.get("job", {}).get("skills", []),
            })

        db["company_match_history"].insert_one({
            "email": current_user.id,
            "jd_text": job_description[:3000],
            "jd_tech": sorted(list(jd_tech)),
            "results": history_results,
            "ran_at": datetime.now(timezone.utc),
        })

        return render_template("results.html", matched_resumes=matched_resumes)

    # GET
    return render_template('job_desc.html')


@app.route('/company/history')
@login_required
def company_history():
    if current_user.user_type != 'company':
        abort(403)

    client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
    db = client["candidates"]

    runs = list(
        db["company_match_history"]
        .find({"email": current_user.id})
        .sort("ran_at", -1)
    )

    # normalise for template
    for r in runs:
        r["_id"] = str(r.get("_id"))
        jdt = (r.get("jd_text") or "").strip()
        r["jd_preview"] = (jdt[:180] + "…") if len(jdt) > 180 else jdt
        # pre-compute “top 3” for the table
        top = (r.get("results") or [])[:3]
        r["top3"] = [{
            "candidate_name": t.get("candidate_name"),
            "match_score": t.get("match_score"),
            "success_rate": t.get("success_rate"),
            "resume_id": t.get("resume_id"),
        } for t in top]

    return render_template("company_history.html", runs=runs)



@app.route('/company/history/clear', methods=['POST'])
@login_required
def clear_company_history():
    if current_user.user_type != 'company':
        abort(403)

    client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
    db = client["candidates"]

    db["company_match_history"].delete_many({"email": current_user.id})

    flash("Company match history cleared.", "success")
    return redirect(url_for('company_history'))


# ===========================================================================================================
# Routes: Shared / Utilities
# ===========================================================================================================
@app.route('/fetch_resume/<resume_id>')
def fetch_resume(resume_id):
    client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
    db = client["candidates"]
    fs = GridFS(db)

    # Lookup doc to get stored filename
    doc = db["candidates"].find_one({"resume_id": ObjectId(resume_id)})
    filename = (doc.get("resume_filename") if doc else None) or f"{resume_id}.pdf"

    resume_file = fs.get(ObjectId(resume_id))
    return send_file(resume_file, mimetype='application/pdf', as_attachment=True, download_name=filename)


@app.route('/history/delete/<entry_id>', methods=['POST'])
@login_required
def delete_history_entry(entry_id):
    client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
    db = client["candidates"]

    if current_user.user_type == 'candidate':
        db["compare_history"].delete_one({"_id": ObjectId(entry_id), "email": current_user.id})
        return redirect(url_for('candidate_history'))

    if current_user.user_type == 'company':
        db["company_match_history"].delete_one({"_id": ObjectId(entry_id), "email": current_user.id})
        return redirect(url_for('company_history'))

    abort(403)


# ===========================================================================================================
# Entrypoint
# ===========================================================================================================
if __name__ == '__main__':
    app.run(debug=True)
