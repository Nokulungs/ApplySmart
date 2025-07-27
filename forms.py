from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange
from wtforms import HiddenField

class ApplicationForm(FlaskForm):
    student_name = StringField('Full Name', validators=[DataRequired()])
    university = SelectField('University', coerce=int, validators=[DataRequired()])
    subjects_data = HiddenField('Subjects Data', validators=[DataRequired()])  # holds JSON string of subjects and points
    submit = SubmitField('Calculate APS & Apply')
