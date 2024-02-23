from app import app

from flask import render_template, redirect, url_for, flash, request, session

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user

from app.forms import RegisterForm, LoginForm, ChangeUsernameForm, ResetPasswordForm, ContactForm

from datetime import datetime
import os

from flask_mail import Mail, Message
from app.mail import EmailSend
from app.mail import *
from secrets import token_urlsafe
import re


import tensorflow as tf
import numpy as np

import plotly.express as px
import pandas as pd


# Load the model from the SavedModel directory
model = tf.saved_model.load("app/final_model")
class_names = ['fabric', 'glass', 'leather', 'metal', 'paper', 'plastic']
img_height = 250
img_width = 250


# Configure Flask app
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['STATIC_FOLDER'] = 'static'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///material_classification.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False



# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com' 
app.config['MAIL_PORT'] = 587 
app.config['MAIL_USE_TLS'] = True 
app.config['MAIL_USERNAME'] = sender_email 
app.config['MAIL_PASSWORD'] = sender_password


db = SQLAlchemy(app)
mail = Mail(app)

# Define User and Materials models
with app.app_context():
    class User(UserMixin, db.Model):
        __tablename__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(70), nullable=False, unique=True)
        email = db.Column(db.String(150), nullable=False, unique=True)
        password = db.Column(db.String(100), nullable=False)
        confirmed = db.Column(db.Boolean, default=False)
        confirm_token = db.Column(db.String(100))

        materials = relationship("Materials", back_populates='user')

    class Materials(db.Model):
        __tablename__ = 'materials'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
        user = relationship("User", back_populates="materials")
        material = db.Column(db.String(200), nullable=False)
        date = db.Column(db.Date, nullable=False, default=datetime.now().date())

    # Create database tables
    db.create_all()

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@login_manager.unauthorized_handler
def unauthorized():
    session['next_url'] = request.url
    # Redirect the user to the login page if they are not authenticated
    flash('You must be logged in first', 'danger')
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------------------------------------------------------------


# all Flask routes below
@app.route("/")
def home():
    material = Materials.query.order_by(Materials.id.desc()).first()

    # Create a DataFrame for plotting
    df = pd.DataFrame([(m.date, m.material) for m in Materials.query.all()], columns=['date', 'material'])
    
    # Count the occurrences of each material and create a new dataframe for bar chart
    df_for_bar = df['material'].value_counts().reset_index()
    df_for_bar.columns = ['material', 'count']

    # Create a bar chart for material counts
    material_counts_graph = px.bar(df_for_bar, x='material', y='count', title='Material Counts')

    # Group by date and count the occurrences of each material
    material_counts = df.groupby('date')['material'].count().reset_index()

    # Create a line chart using Plotly Express
    requests_by_date_graph = px.line(material_counts, x='date', y='material', labels={'date': 'Date', 'material': 'Material Count'}, title='Number of predictions by date')
  
    material_bar_chart_html = material_counts_graph.to_html(full_html=False)
    material_line_chart_html = requests_by_date_graph.to_html(full_html=False)

    # Check if there is an uploaded image\
    filename = ''
    filenames = os.listdir(app.config['UPLOAD_FOLDER'])
    if filenames:
        filename = sorted(filenames, reverse=True)[0]  # Latest file
    else:
        filename = ''
    
    return render_template('index.html', image_filename=filename, material=material, material_bar_chart_html=material_bar_chart_html,material_line_chart_html=material_line_chart_html)


app.config['UPLOAD_FOLDER'] = 'app/static/uploaded_img'
app.config['ALLOWED_IMAGE_EXTENSIONS'] = ['PNG','JPG','JPEG',"GIF"]

def allowed_file(filename):
    if not '.' in filename:
        return False
    
    if filename.split('.')[-1].upper() in app.config['ALLOWED_IMAGE_EXTENSIONS']:
        return True
    
    else: 
        return False
    

@app.route('/upload-image/', methods=['GET', 'POST'])
@login_required
def upload_image():
    if request.method == 'POST':
        if 'image' not in request.files:
            flash('No image part', 'danger')
            return redirect(request.url)

        file = request.files['image']

        if file.filename == '':
            flash('No image selected for uploading', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Save the file
            file.save(file_path)
            flash('Image successfully uploaded and displayed below', 'success')

            # Load the saved image using TensorFlow
            img = tf.keras.utils.load_img(file_path, target_size=(img_height, img_width))
            img_array = tf.keras.utils.img_to_array(img)
            img_array = tf.expand_dims(img_array, 0)

            # Make predictions using the SavedModel
            predictions = model(tf.constant(img_array))
            predicted_class = class_names[np.argmax(predictions.numpy())]

            # Save the material information to the database
            current_user_id = current_user.id if current_user.is_authenticated else None
            new_object = Materials(
                user_id=current_user_id,
                material=predicted_class
            )
            db.session.add(new_object)
            db.session.commit()

            return redirect(url_for('home'))

    return render_template('upload_image.html')

# deleting the image from the uploaded folder
@app.route("/delete-image", methods=["POST"])
def delete_image():
    filenames = os.listdir(app.config['UPLOAD_FOLDER'])
    if filenames:
        filename = sorted(filenames, reverse=True)[0]
        if filename:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))


# Helper function to generate a confirmation token
def generate_confirmation_token():
    return token_urlsafe(30)

# Helper function to send confirmation emails
def send_confirmation_email(user):
    token = user.confirm_token
    confirm_url = url_for('confirm_email', token=token, _external=True)
    subject = "Confirm Your Email"
    message = f"Thanks for signing up with Material Classification App. Please confirm your email by clicking the following link: \n {confirm_url}"
    msg = Message(subject, sender=sender_email, recipients=[user.email])
    msg.body = message
    mail.send(msg)

# Helper function to validate email format
def is_valid_email(email):
    if re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return True
    return False

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('You are already logged in. Please logout to Register a new account.', 'danger')
        return redirect(url_for('profile', username=current_user.username))

    register_form = RegisterForm()

    if register_form.validate_on_submit():
        entered_email = register_form.email.data.lower()
        entered_username = register_form.username.data.lower()

        if not is_valid_email(entered_email):
            flash('Invalid email format. Please enter a valid email address.', 'danger')
            return redirect(url_for('register'))

        elif User.query.filter_by(email=entered_email).first():
            flash('A user with that email already exists. Please log in or use another email.', 'danger')
            return redirect(url_for('login'))

        elif User.query.filter_by(username=entered_username).first():
            flash('A user with that username already exists. Please choose another username.', 'danger')
            return redirect(url_for('register'))
        else:
            hashed_and_salted_password = generate_password_hash(password=register_form.password.data, method="pbkdf2:sha256", salt_length=8)
            confirmation_token = generate_confirmation_token()
            new_user = User(username=entered_username, email=entered_email, password=hashed_and_salted_password, confirmed=False, confirm_token=confirmation_token)
            db.session.add(new_user)
            db.session.commit()

            send_confirmation_email(new_user)

            flash('Please check your email for a confirmation link.', 'success')
            return redirect(url_for('login'))

    return render_template("register.html", form=register_form)

# Confirmation route (continued)
@app.route('/confirm/<token>', methods=['GET'])
def confirm_email(token):
    user = User.query.filter_by(confirm_token=token).first()
    
    if user:
        if not user.confirmed:
            user.confirmed = True
            user.confirm_token = None
            db.session.add(user)
            db.session.commit()
            flash('Email confirmed. You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email already confirmed. You can log in.', 'info')
            return redirect(url_for('login'))
    else:

        flash('Invalid or expired confirmation link. Please register again.', 'danger')
        return redirect(url_for('register'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('You are already logged in. Please logout to login again or register a new account.', 'danger')
        return redirect(url_for('profile', username=current_user.username))

    login_form = LoginForm()

    if login_form.validate_on_submit():
        entered_email = login_form.email.data
        entered_password = login_form.password.data
        user = User.query.filter_by(email=entered_email).first()

        if not user:
            flash('No user found with that email. Please try again or register.', 'danger')
            login_form.email.data = entered_email
            return redirect(url_for('login'))

        if not user.confirmed:
            flash('Please confirm your email address to log in.', 'danger')
            return redirect(url_for('login'))

        if not check_password_hash(pwhash=user.password, password=entered_password):
            flash('Invalid password. Please try again.', 'danger')
            login_form.email.data = entered_email
            return redirect(url_for('login'))

        login_user(user)
        next_url = session.get('next_url')
        if next_url:
            # Clear the stored next_url from the session
            session.pop('next_url', None)
            # Redirect the user back to the original URL
            return redirect(next_url)
        return redirect(url_for('home'))

    return render_template("login.html", form=login_form)

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'primary')
    return redirect(url_for('login'))


@app.route('/profile/<username>/')
@login_required
def profile(username):
    
    user = User.query.filter_by(username=username).first_or_404()

    # prevent other users to enter others profile.
    if user.id != current_user.id:
        flash("You can only access to your profile",'danger')
        return redirect(url_for('profile',username=current_user.username))

    # Fetch data from the Materials table for the current user
    user_materials = Materials.query.filter_by(user_id=current_user.id).all()

    # Create a DataFrame for plotting
    user_df = pd.DataFrame([(m.date, m.material) for m in user_materials], columns=['date', 'material'])
    
    # Count the occurrences of each material and define a new df for bar chart
    user_df_for_bar = user_df['material'].value_counts().reset_index()
    user_df_for_bar.columns = ['material', 'count']
    # Create a bar chart for material counts
    user_material_counts_graph = px.bar(user_df_for_bar, x='material', y='count',title='Material Counts')

    # Group by date and count the occurrences of each material
    user_material_counts = user_df.groupby('date')['material'].count().reset_index()

    # Create a line chart using Plotly Express
    user_requests_by_date_graph = px.line(user_material_counts, x='date', y='material', labels={'date': 'Date', 'material': 'Material Count'}, title='Number of predictions by date')
  
    user_material_bar_chart_html = user_material_counts_graph.to_html(full_html=False)
    user_material_line_chart_html = user_requests_by_date_graph.to_html(full_html=False)
    
    return render_template('profile.html',user=user,user_material_bar_chart_html=user_material_bar_chart_html,user_material_line_chart_html=user_material_line_chart_html)


@app.route('/change_username/<username>/',methods=["GET","POST"])
@login_required
def change_username(username):
    user = User.query.filter_by(username=username).first_or_404()

    change_username_form = ChangeUsernameForm(obj=user)

    if current_user.id == user.id:
        if change_username_form.validate_on_submit():

            if User.query.filter_by(username=change_username_form.username.data.lower()).first():
                flash("This username already exists",'danger')
            
            else:
                user.username = change_username_form.username.data.lower()

                db.session.commit()
                flash('Your Username Was Updated Successfully','success')
                return redirect(url_for('profile',username=current_user.username))

    else:
        flash("You can only edit Your Details",'danger')
        return redirect(url_for('profile',username=current_user.username))
    
    return render_template('change_username.html', form=change_username_form)

@app.route('/reset_password/<username>/',methods=['GET','POST'])
@login_required
def reset_password(username):
    user = User.query.filter_by(username=username).first_or_404()
    reset_password_form = ResetPasswordForm()

    if current_user.id == user.id:

        if reset_password_form.validate_on_submit():
            old_entered_password = reset_password_form.old_password.data
            if not check_password_hash(pwhash=user.password, password=old_entered_password):
                flash('The old password is incorrect,please try again','danger')
                return redirect(url_for('reset_password',username=user.username))
            
            if old_entered_password == reset_password_form.new_password.data:
                flash("Please choose different new password from your old one", 'danger')

            else:
                hashed_and_salted_password = generate_password_hash(
                    password=reset_password_form.new_password.data, 
                    method="pbkdf2:sha256",salt_length=8)
                
                user.password = hashed_and_salted_password

                db.session.commit()
                logout_user()
                flash('Your Password Was Reset Successfully. Please now Log In','success')
                return redirect(url_for('login'))

    else:
        flash("You can only Reset Your Password",'danger')
        return redirect(url_for('profile',username=current_user.username))
    
    return render_template('reset_password.html', form=reset_password_form)

@app.route('/about/')
def about():
    return render_template('about.html')


email_sender = EmailSend()
@app.route('/contact/',methods=['POST', 'GET'])
def contact():
    form = ContactForm()
    if current_user.is_authenticated:
        form.name.data = current_user.username
        form.email.data = current_user.email

    try:
        if form.validate_on_submit():
            name = form.name.data
            email = form.email.data
            subject = form.subject.data
            message = form.message.data
            files = form.files.data

            email_sender.send_email(name,email,subject,message,files)
            flash('Email was sent successfully. We will contact you.','success' )
            return redirect(url_for('contact'))
    except:
        flash('Error. Email was not sent. Please try again.','danger' )
        return redirect(url_for('contact'))
        
    return render_template('contact.html',form=form)
