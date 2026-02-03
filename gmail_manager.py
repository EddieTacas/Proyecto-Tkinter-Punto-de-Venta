
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

def send_email(sender_email, app_password, receivers_list, subject, body_text):
    """
    Sends an email using Gmail SMTP in a separate thread.
    receivers_list: list of email strings
    """
    def _send():
        try:
            # Setup server
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            
            # Login
            server.login(sender_email, app_password)
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ", ".join(receivers_list)
            msg['Subject'] = subject
            
            # Attach body
            msg.attach(MIMEText(body_text, 'plain'))
            
            # Send
            server.sendmail(sender_email, receivers_list, msg.as_string())
            server.quit()
            print(f"Email sent successfully to {receivers_list}")
            
        except Exception as e:
            print(f"Failed to send email: {e}")

    # Run in thread to not block UI
    threading.Thread(target=_send, daemon=True).start()
