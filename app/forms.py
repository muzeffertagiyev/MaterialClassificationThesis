from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, EmailField,TextAreaField, MultipleFileField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError


class RegisterForm(FlaskForm):
    username = StringField( validators=[DataRequired(),Length(min=4, max=30)])
    email = EmailField(validators=[DataRequired(),Length(min=4, max=300) ,Email()])
    password = PasswordField(validators=[DataRequired(), Length(min=8,max=300)])
    confirm_password = PasswordField(validators=[
        DataRequired(),Length(min=8,max=300),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField()

class LoginForm(FlaskForm):
    email = StringField(validators=[DataRequired(),Length(max=100)])
    password = PasswordField(validators=[DataRequired(),Length(min=8, max=150)])
    submit = SubmitField()


class ContactForm(FlaskForm):
    name = StringField(validators=[DataRequired(),Length(min=4, max=50)])
    email = EmailField(validators=[DataRequired(),Length(min=4, max=150) ,Email()])
    subject = StringField(validators=[DataRequired(),Length(min=4, max=200)])
    message = TextAreaField(validators=[DataRequired()])
    files = MultipleFileField()
    submit = SubmitField()


class ChangeUsernameForm(FlaskForm):
    username = StringField( validators=[DataRequired(),Length(min=4, max=200)])
    submit = SubmitField()


class ResetPasswordForm(FlaskForm):
    old_password = PasswordField( validators=[DataRequired(), Length(min=8, max=150)])
    new_password = PasswordField(validators=[DataRequired(), Length(min=8,max=150)])
    new_confirm_password = PasswordField( validators=[
        DataRequired(),Length(min=8,max=150),
        EqualTo('new_password', message='Passwords must match.')
    ])

    submit = SubmitField()
