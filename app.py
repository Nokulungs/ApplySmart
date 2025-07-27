from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length
import json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# In-memory user store: username -> password_hash
users_db = {}

UNIVERSITY_COURSES = {
    1: {
        "name": "Tshwane University of Technology",
        "website": "https://www.tut.ac.za",
        "courses": {
            "Computer Science": {
                "min_aps": 30,
                "url": "https://applications-prod.tut.ac.za/",
                "required_subjects": {"Mathematics": 5, "PhysicalScience": 4}
            },
            "Business": {
                "min_aps": 25,
                "url": "https://applications-prod.tut.ac.za/",
                "required_subjects": {}  # No specific subjects required
            },
            "Engineering": {
                "min_aps": 35,
                "url": "https://applications-prod.tut.ac.za/",
                "required_subjects": {"Mathematics": 6, "PhysicalScience": 5}
            },
        }
    },
    2: {
        "name": "University of Johannesburg",
        "website": "https://www.uj.ac.za",
        "courses": {
            "Law": {
                "min_aps": 28,
                "url": "https://www.uj.ac.za/admissions-aid/",
                "required_subjects": {}
            },
            "Medicine": {
                "min_aps": 38,
                "url": "https://www.uj.ac.za/admissions-aid/",
                "required_subjects": {"LifeScience": 6, "Mathematics": 5}
            },
            "Arts": {
                "min_aps": 20,
                "url": "https://www.uj.ac.za/admissions-aid/",
                "required_subjects": {}
            },
        }
    }
}

# Forms (unchanged) ...

class SignUpForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ApplicationForm(FlaskForm):
    student_name = StringField('Full Name', validators=[DataRequired()])
    university = SelectField('University', coerce=int, validators=[DataRequired()])
    subjects_data = TextAreaField('Subjects Data (JSON)', validators=[DataRequired()])
    submit = SubmitField('Calculate APS & Apply')

# User helpers (unchanged) ...

def signup_user(username, password):
    username = username.lower()
    if username in users_db:
        return False, "User already exists"
    password_hash = generate_password_hash(password)
    users_db[username] = password_hash
    return True, "User created successfully"

def validate_login(username, password):
    username = username.lower()
    if username in users_db and check_password_hash(users_db[username], password):
        return True
    return False

# APS calculation (unchanged) ...

def calculate_aps(marks_dict):
    aps = 0
    for mark in marks_dict.values():
        if mark >= 80:
            aps += 7
        elif mark >= 70:
            aps += 6
        elif mark >= 60:
            aps += 5
        elif mark >= 50:
            aps += 4
        elif mark >= 40:
            aps += 3
        elif mark >= 30:
            aps += 2
        else:
            aps += 1
    return aps

# Routes (mostly unchanged except /results)

@app.route('/')
def landing():
    if 'user_id' in session:
        return redirect(url_for('apply'))
    return render_template('landing.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('apply'))
    form = SignUpForm()
    if form.validate_on_submit():
        success, msg = signup_user(form.username.data, form.password.data)
        if success:
            flash(msg, 'success')
            return redirect(url_for('login'))
        else:
            flash(msg, 'error')
    return render_template('signup.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('apply'))
    form = LoginForm()
    if form.validate_on_submit():
        if validate_login(form.username.data, form.password.data):
            session['user_id'] = form.username.data.lower()
            flash('Logged in successfully!', 'success')
            return redirect(url_for('apply'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out.', 'info')
    return redirect(url_for('landing'))

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if 'user_id' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))

    form = ApplicationForm()
    form.university.choices = [(uid, uni["name"]) for uid, uni in UNIVERSITY_COURSES.items()]

    if form.validate_on_submit():
        try:
            subjects = json.loads(form.subjects_data.data)
        except json.JSONDecodeError:
            flash('Invalid subjects data submitted.', 'error')
            return render_template('apply.html', form=form)

        if len(subjects) < 7:
            flash("Please enter at least 7 subjects.", 'error')
            return render_template('apply.html', form=form)

        aps_score = sum(s['point'] for s in subjects)
        session['student_name'] = form.student_name.data
        session['university_id'] = form.university.data
        session['aps_score'] = aps_score
        session['subjects'] = subjects

        return redirect(url_for('results'))

    return render_template('apply.html', form=form)

@app.route('/results')
def results():
    aps_score = session.get('aps_score')
    university_id = session.get('university_id')
    subjects = session.get('subjects', [])

    if aps_score is None or university_id is None:
        return redirect(url_for('apply'))

    courses = UNIVERSITY_COURSES[university_id]['courses']

    # Normalize user subjects: keys lowercase
    user_subjects = {sub['name'].strip().lower(): sub['point'] for sub in subjects}

    qualifying_courses = []
    for course_name, details in courses.items():
        if aps_score < details['min_aps']:
            continue

        # Normalize required subjects keys to lowercase
        required_subs = {k.lower(): v for k, v in details.get('required_subjects', {}).items()}

        meets_required_subjects = True
        for req_sub, req_min_aps in required_subs.items():
            if req_sub not in user_subjects or user_subjects[req_sub] < req_min_aps:
                meets_required_subjects = False
                break

        if meets_required_subjects:
            qualifying_courses.append({"name": course_name, "url": details["url"]})

    return render_template(
        'results.html',
        student_name=session.get('student_name'),
        aps_score=aps_score,
        qualifying_courses=qualifying_courses,
        university=UNIVERSITY_COURSES[university_id]['name']
    )

if __name__ == '__main__':
    app.run(debug=True)
