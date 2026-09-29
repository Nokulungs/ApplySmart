from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, SubmitField, HiddenField
from wtforms.validators import DataRequired, EqualTo, Length
import json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-to-a-random-secret-in-production'


# ============================================================
# IN-MEMORY USER STORE
# ============================================================
# username (lowercase) -> password_hash
users_db = {}


# ============================================================
# UNIVERSITY DATA
# ============================================================
UNIVERSITY_COURSES = {
    1: {
        "name": "Tshwane University of Technology",
        "website": "https://www.tut.ac.za",
        "courses": {
            "Computer Science": {
                "min_aps": 30,
                "url": "https://applications-prod.tut.ac.za/",
                "required_subjects": {"mathematics": 5, "physicalscience": 4}
            },
            "Business": {
                "min_aps": 25,
                "url": "https://applications-prod.tut.ac.za/",
                "required_subjects": {}
            },
            "Engineering": {
                "min_aps": 35,
                "url": "https://applications-prod.tut.ac.za/",
                "required_subjects": {"mathematics": 6, "physicalscience": 5}
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
                "required_subjects": {"lifescience": 6, "mathematics": 5}
            },
            "Arts": {
                "min_aps": 20,
                "url": "https://www.uj.ac.za/admissions-aid/",
                "required_subjects": {}
            },
        }
    }
}


# ============================================================
# FORMS
# ============================================================
class SignUpForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )
    submit = SubmitField('Create Account')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')


class ApplicationForm(FlaskForm):
    student_name = StringField('Full Name', validators=[DataRequired()])
    university = SelectField('University', coerce=int, validators=[DataRequired()])
    subjects_data = HiddenField('Subjects Data')   # HiddenField — the JS sets JSON here
    submit = SubmitField('Calculate My APS')


# ============================================================
# USER HELPERS
# ============================================================
def signup_user(username, password):
    username = username.lower().strip()
    if username in users_db:
        return False, "That username is already taken."
    password_hash = generate_password_hash(password)
    users_db[username] = password_hash
    return True, "Account created! You can now sign in."


def validate_login(username, password):
    username = username.lower().strip()
    if username in users_db and check_password_hash(users_db[username], password):
        return True
    return False


# ============================================================
# APS CALCULATION
# ============================================================
def calculate_aps_from_marks(marks_dict):
    """
    Convenience helper if you ever want to compute APS from raw marks (0-100)
    instead of already-converted 1-7 points.
    """
    aps = 0
    for mark in marks_dict.values():
        if mark >= 80:   aps += 7
        elif mark >= 70: aps += 6
        elif mark >= 60: aps += 5
        elif mark >= 50: aps += 4
        elif mark >= 40: aps += 3
        elif mark >= 30: aps += 2
        else:            aps += 1
    return aps


# ============================================================
# ROUTES
# ============================================================
@app.route('/')
def index():                                   # ← named 'index' to match your templates
    if 'user_id' in session:
        return redirect(url_for('apply'))
    return render_template('index.html')


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
            session['user_id'] = form.username.data.lower().strip()
            flash('Welcome back!', 'success')
            return redirect(url_for('apply'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if 'user_id' not in session:
        flash('Please sign in to continue.', 'error')
        return redirect(url_for('login'))

    form = ApplicationForm()
    form.university.choices = [(uid, uni["name"]) for uid, uni in UNIVERSITY_COURSES.items()]

    if form.validate_on_submit():
        # ---- Parse subjects JSON sent from the client ----
        try:
            subjects = json.loads(form.subjects_data.data or "[]")
        except (json.JSONDecodeError, TypeError):
            flash('There was a problem reading your subjects. Please try again.', 'error')
            return render_template('apply.html', form=form)

        if len(subjects) < 7:
            flash('Please add at least 7 subjects.', 'error')
            return render_template('apply.html', form=form)

        # ---- Calculate APS from the 1-7 points the user entered ----
        aps_score = sum(int(s['point']) for s in subjects)

        # ---- Store in session for the results page ----
        session['student_name']  = form.student_name.data
        session['university_id'] = form.university.data
        session['aps_score']     = aps_score
        session['subjects']      = subjects

        return redirect(url_for('results'))

    return render_template('apply.html', form=form)


@app.route('/results')
def results():
    aps_score     = session.get('aps_score')
    university_id = session.get('university_id')
    subjects      = session.get('subjects', [])
    student_name  = session.get('student_name')

    # No data in session → user landed here directly, send them back
    if aps_score is None or university_id is None:
        flash('Please submit an application first.', 'error')
        return redirect(url_for('apply'))

    university = UNIVERSITY_COURSES.get(university_id)
    if university is None:
        flash('Unknown university selected.', 'error')
        return redirect(url_for('apply'))

    courses = university['courses']

    # Normalize user subjects: {'mathematics': 6, 'english': 5, ...}
    user_subjects = {sub['name'].strip().lower(): int(sub['point']) for sub in subjects}

    qualifying_courses = []
    for course_name, details in courses.items():
        # 1) APS gate
        if aps_score < details['min_aps']:
            continue

        # 2) Required-subject gate
        required_subs = details.get('required_subjects', {})
        meets_required = True
        for req_sub, req_min in required_subs.items():
            if user_subjects.get(req_sub, 0) < req_min:
                meets_required = False
                break

        if meets_required:
            qualifying_courses.append({
                "name": course_name,
                "url":  details["url"]
            })

    return render_template(
        'results.html',
        student_name=student_name,
        aps_score=aps_score,
        qualifying_courses=qualifying_courses,
        university=university['name']
    )


# ============================================================
# RUN
# ============================================================
if __name__ == '__main__':
    app.run(debug=True)