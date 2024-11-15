import base64
import os
import mimetypes
import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]

def authorize():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    flow.run_local_server(port=0, prompt='consent')
    credentials = flow.credentials
    return credentials

def list_emails(start_date_str, end_date_str, credentials):
    service = build('gmail', 'v1', credentials=credentials)
    try:        
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        query = f"after:{start_date.strftime('%Y/%m/%d')} before:{end_date.strftime('%Y/%m/%d')}"
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], q=query).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No emails found within the specified date range.')
        else:
            print('Emails within the date range:')
            for message in messages:
                email = service.users().messages().get(userId='me', id=message['id']).execute()
                sender = ''
                subject = ''
                for header in email['payload']['headers']:                    
                    if header['name'] == 'From':
                        if '<' in header['value']:
                            sender = header['value'].split('<')[1][:-1]
                    if header['name'] == 'Subject':
                        subject = header['value']

                print('- EmailID:', email["id"], '- Subject:', subject, '- From:', sender)

    except HttpError as error:
        print(f'An error occurred: {error}')

def reply_to_email(email_id, reply_body, credentials):
    service = build('gmail', 'v1', credentials=credentials)
    try:
        msg = service.users().messages().get(userId='me', id=email_id).execute()
        to_email = ''
        from_email = ''
        subject = ''
        message_id = ''

        for header in msg['payload']['headers']:
            if header['name'] == 'To':
                if '<' in header['value']:
                    to_email = header['value'].split('<')[1][:-1]
            if header['name'] == 'From':
                if '<' in header['value']:
                    from_email = header['value'].split('<')[1][:-1]
            if header['name'] == 'Subject':
                subject = header['value']
            if header['name'] == 'Message-ID':
                message_id = header['value']
        
        reply_message = create_message(
            thread_id=email_id,
            sender=to_email,
            to=from_email,
            subject='Re: ' + subject,
            message_text=reply_body,
            message_id=message_id
        )

        service.users().messages().send(userId='me', body=reply_message).execute()
        print('Reply sent successfully.')
    except HttpError as error:
        print(f'An error occurred: {error}')

def create_message(thread_id, sender, to, subject, message_text, message_id):
    message = {
        'to': to,
        'subject': subject,
        'threadId': thread_id,
        'labelIds': ['INBOX'],
        'raw': base64.urlsafe_b64encode(
            f"From: {sender}\r\n"
            f"To: {to}\r\n"
            f"Subject: {subject}\r\n"
            f'In-Reply-To: {message_id}\r\n'
            f'References: {message_id}\r\n\r\n'
            f"{message_text}"
            .encode('utf-8')
        ).decode('utf-8')
    }

    return message

def get_user_email(credentials):
    service = build('gmail', 'v1', credentials=credentials)
    try:
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile['emailAddress']
        return email_address
    except Exception as e:
        print('An error occurred while retrieving the user email:', str(e))

def attach_file_to_email(from_address, to_address, message_subject, reply_body, file_path, credentials):
    service = build('gmail', 'v1', credentials=credentials)
    try:
        reply_message = create_message_with_attachment(
            sender=from_address,
            to=to_address,
            subject=message_subject,
            message_text=reply_body,
            file_path=file_path
        )

        service.users().messages().send(userId='me', body=reply_message).execute()
        print('File attached and email sent successfully.')
    except HttpError as error:
        print(f'An error occurred: {error}')

def create_message_with_attachment(sender, to, subject, message_text, file_path):
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    msg = MIMEText(message_text)
    message.attach(msg)

    content_type, encoding = mimetypes.guess_type(file_path)
    if content_type is None or encoding is not None:
        content_type = 'application/octet-stream'
    main_type, sub_type = content_type.split('/', 1)
    with open(file_path, 'rb') as file:
        attachment = MIMEBase(main_type, sub_type)
        attachment.set_payload(file.read())
    encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file_path))
    message.attach(attachment)

    return {
        'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()
    }

credentials = authorize()

# Example usage
start_date_str = input('Enter the start date (YYYY-MM-DD): ')
end_date_str = input('Enter the end date (YYYY-MM-DD): ')
list_emails(start_date_str, end_date_str, credentials)

email_id = input('Enter the email id: ')
message_body = input('Enter the message body: ')
reply_to_email(email_id, message_body, credentials)

from_address = get_user_email(credentials)
to_address = input('Enter the email address: ')
message_subject = input('Enter the message subject: ')
message_body = input('Enter the message body: ')
file_path = input('Enter file path: ')
attach_file_to_email(from_address, to_address, message_subject, message_body, file_path, credentials)