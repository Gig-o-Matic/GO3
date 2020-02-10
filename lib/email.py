from django.template.loader import render_to_string
from django_q.tasks import async_task
from markdown import markdown

from go3.settings import SERVER_EMAIL

SUBJECT = 'Subject:'
DEFAULT_SUBJECT = 'Message from Gig-O-Matic'

def send_mail_async(subject, message, from_email, recipient_list, html_message=None):
    async_task('django.core.mail.send_mail',
               subject=subject,
               message=message,
               from_email=from_email,
               recipient_list=recipient_list,
               html_message=html_message,
               ack_failure=True
              )

def send_markdown_mail(template, context, recipient_list, from_email=SERVER_EMAIL):
    text = render_to_string(template, context)
    if text.startswith(SUBJECT):
        subject, text = [t.strip() for t in text[len(SUBJECT):].split('\n', 1)]
    else:
        subject = DEFAULT_SUBJECT
    html = markdown(text)
    send_mail_async(subject, text, from_email, recipient_list, html)
