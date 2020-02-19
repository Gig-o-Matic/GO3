from django.core import mail
from django_q.tasks import async_task

SUBJECT = 'Subject:'
DEFAULT_SUBJECT = 'Message from Gig-O-Matic'

def send_messages_async(messages):
    # Can accept an iterable, so we need to make it a list for serialization
    return async_task('lib.email.do_send_messages_async', list(messages), ack_failure=True)

def do_send_messages_async(messages):
    mail.get_connection().send_messages(messages)
