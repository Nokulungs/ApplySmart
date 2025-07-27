from extensions import db

class University(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    courses = db.relationship('Course', backref='university', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    min_aps = db.Column(db.Integer, nullable=False)  # Minimum APS score required
    university_id = db.Column(db.Integer, db.ForeignKey('university.id'), nullable=False)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id'), nullable=False)
    aps_score = db.Column(db.Integer, nullable=False)
    marks = db.Column(db.String(200))  # You can store marks as JSON string for simplicity
