import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

class EmailSender:
    def __init__(self, smtp_server, port, username, password, use_tls=True):
        """
        Initialise le client SMTP.
        
        :param smtp_server: Adresse du serveur SMTP.
        :param port: Port du serveur SMTP.
        :param username: Nom d'utilisateur pour l'authentification.
        :param password: Mot de passe pour l'authentification.
        :param use_tls: Utiliser TLS pour sécuriser la connexion.
        """
        self.smtp_server = smtp_server
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def send_email(self, sender_email, recipient_email, subject, body, attachments=None):
        """
        Envoie un e-mail.
        
        :param sender_email: Adresse e-mail de l'expéditeur.
        :param recipient_email: Adresse e-mail du destinataire.
        :param subject: Sujet de l'e-mail.
        :param body: Contenu de l'e-mail.
        :param attachments: Liste des chemins des fichiers à joindre (facultatif).
        """
        try:
            # Crée le message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject

            # Ajoute le corps de l'e-mail
            msg.attach(MIMEText(body, 'plain'))

            # Ajoute les pièces jointes, si elles existent
            if attachments:
                for file_path in attachments:
                    attachment = MIMEBase('application', 'octet-stream')
                    with open(file_path, 'rb') as file:
                        attachment.set_payload(file.read())
                    encoders.encode_base64(attachment)
                    attachment.add_header(
                        'Content-Disposition',
                        f'attachment; filename={file_path.split("/")[-1]}'
                    )
                    msg.attach(attachment)

            # Connexion au serveur SMTP
            with smtplib.SMTP(self.smtp_server, self.port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(sender_email, recipient_email, msg.as_string())

            print(f"E-mail envoyé avec succès à {recipient_email}")

        except Exception as e:
            print(f"Erreur lors de l'envoi de l'e-mail : {e}")

# Exemple d'utilisation
if __name__ == "__main__":
    smtp_server = "smtp.gmail.com"
    port = 587
    username = "votre_email@gmail.com"
    password = "votre_mot_de_passe"

    email_sender = EmailSender(smtp_server, port, username, password)
    email_sender.send_email(
        sender_email="votre_email@gmail.com",
        recipient_email="destinataire@example.com",
        subject="Test d'envoi d'e-mail",
        body="Ceci est un test d'e-mail envoyé depuis Python.",
        attachments=["/chemin/vers/fichier.pdf"]
    )