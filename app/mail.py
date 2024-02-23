import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from werkzeug.datastructures import FileStorage

import requests

email_api_endpoint = 'https://api.npoint.io/700baf4dcaef21388e91'

response = requests.get(email_api_endpoint)
email_data = response.json()

to_email = email_data['to_email']
sender_email = email_data['sender_email']['email']
sender_password = email_data['sender_email']['password']

class EmailSend:

    def send_email(self,name,email,subject,message,files):
        
                
        with smtplib.SMTP(host='smtp.gmail.com',port=587) as connection:
            
            connection.starttls()
            connection.login(user=sender_email, password=sender_password)
            
            email_sending = MIMEMultipart()
            email_sending['From'] = sender_email
            email_sending['To'] = to_email
            email_sending['Subject'] = subject
            message_content = f"Name: {name.capitalize()} \nemail: {email} \n\nMessage: \n {message}"
            email_sending.attach(MIMEText(message_content))
            if files:
                for file in files:     
                    if isinstance(file, FileStorage):  # Ensure it's a file object
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(file.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename="{file.filename}"')
                        email_sending.attach(part)

            connection.sendmail(from_addr=sender_email, to_addrs=to_email, msg=email_sending.as_string())

