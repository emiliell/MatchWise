from flask import Flask, request, render_template, jsonify
import spacy
from pymongo import MongoClient
from gridfs import GridFS
from flask import send_file
from bson import ObjectId
from flask import Flask, render_template, redirect, url_for, flash
from flask import abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from flask_bcrypt import Bcrypt
from wtforms import StringField, PasswordField, SubmitField
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import DataRequired, EqualTo, Email
from dotenv import load_dotenv
import os
import re
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from io import BytesIO
from pdfminer.high_level import extract_text


load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
app.config['SECRET_KEY'] = 'random_key'

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)


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




def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return (inter / union) * 100.0

def extract_required_block(text: str) -> str | None:
    """Return only the 'Required' or 'Must have' block if present."""
    pattern = r"(?:^|\n)\s*(?:required|requirements|must[- ]have)\s*:(.*?)(?:\n\s*\n|$|(?:\n\s*(?:nice to have|preferred|responsibilities|about|description)\s*:))"
    m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else None

def estimate_success(similarity_score: float, jd_text: str, jd_tech: set[str],
                     resume_skills: set[str], nlp) -> float:
    """Success rate (0–100). If a 'Required' block exists, blend in its coverage;
    otherwise, fall back to the similarity score alone."""
    req_block = extract_required_block(jd_text)
    if req_block:
        req_tech = extract_tech(nlp, req_block)
        if req_tech:
            required_coverage = len(req_tech & resume_skills) / len(req_tech)
            success = (0.60 * float(similarity_score)) + (40.0 * required_coverage)
            return round(max(0.0, min(100.0, success)), 1)

    # No required block (or empty after extraction) → use similarity as success
    return round(max(0.0, min(100.0, float(similarity_score))), 1)



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




class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    user_type = StringField('User Type (candidate or company)', validators=[DataRequired()])
    submit = SubmitField('Register')

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


@app.route('/upload_form')
@login_required
def upload_form():
    if current_user.user_type != 'candidate':
        flash('You do not have access to this page', 'danger')
        return redirect('job_desc.html')
    return render_template('upload.html')

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

    
@app.route('/match', methods=['GET', 'POST'])
@login_required
def match():
    if request.method == 'POST':
        user_input = request.form.get('job_description')
        nlp = spacy.load("model_upgrade")
        doc = nlp(user_input)
        technology_names = []
        for ent in doc.ents:
            if ent.label_ in ["ORG", "TECHNOLOGY", "TECH"]:
                technology_names.append(ent.text)

        bef_technology_names = technology_names
        technology_names = list(set(technology_names))
        technology_names = [ele.lower() for ele in technology_names]

        client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
        db = client["candidates"]
        users = db["candidates"]

        user_data = list(users.aggregate([
            {"$match": {"skills": {"$in": technology_names}}},
            {"$addFields": {"matchedSkills": {"$size": {"$setIntersection": ["$skills", technology_names]}}}},
            {"$sort": {"matchedSkills": -1}}
        ]))
        return render_template('view_resumes.html', user_data=user_data, technology_names=bef_technology_names)

    # GET
    return render_template('job_desc.html')


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
        "resume_filename": resume_file.filename
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
    # Build options: (value, label)
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

        jd_tech = extract_tech(nlp, jd_text)
        res_skills = {s.lower() for s in (doc.get('skills') or [])}
        score = round(jaccard(jd_tech, res_skills), 1)

        success_rate = estimate_success(score, jd_text, jd_tech, res_skills, nlp)

        result = {
            "name": doc.get("name"),
            "email": doc.get("email"),
            "resume_id": str(doc.get("resume_id")),
            "resume_filename": doc.get("resume_filename"),
            "score": score,
            "success_rate": success_rate,
            "matched": sorted(list(jd_tech & res_skills)),
        }


        return render_template(
            "candidate_compare.html",
            options=options,
            jd_text=jd_text,
            jd_tech=sorted(list(jd_tech)),
            result=result,
        )

    # GET
    return render_template('candidate_compare.html', options=options)




@app.route('/fetch_resume/<resume_id>')
def fetch_resume(resume_id):
    client = MongoClient(os.getenv("MongoDBURL"), tls=True, tlsAllowInvalidCertificates=True)
    db = client["candidates"]
    fs = GridFS(db)

    #print(fs)

    # Fetching the file from GridFS
    resume_file = fs.get(ObjectId(resume_id))

    # Creating a response with the file data
    response = send_file(resume_file, mimetype='application/pdf', as_attachment=True, download_name=f"{resume_id}.pdf")
    
    return response


if __name__ == '__main__':
    app.run(debug=True)
