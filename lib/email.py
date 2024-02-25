from dataclasses import dataclass

from django.core import mail
from django.template.loader import render_to_string
from django.utils import translation
from django_q.tasks import async_task
from markdown import markdown

from go3.settings import (
    DEFAULT_FROM_EMAIL,
    DEFAULT_FROM_EMAIL_NAME,
    LANGUAGE_CODE,
    URL_BASE,
)

SUBJECT = "Subject:"
DEFAULT_SUBJECT = "Message from Gig-O-Matic"


def send_messages_async(messages):
    # Can accept an iterable, so we need to make it a list for serialization
    return async_task(
        "lib.email.do_send_messages_async", list(messages), ack_failure=True
    )


def do_send_messages_async(messages):
    mail.get_connection().send_messages(messages)


@dataclass
class EmailRecipient:
    email: str
    name: str = ""
    language: str = LANGUAGE_CODE

    @property
    def email_line(self):
        return f"{self.name} <{self.email}>" if self.name else self.email


def prepare_email(recipient, template, context=None, **kw):
    if not context:
        context = dict()
    context["recipient"] = recipient
    context["url_base"] = URL_BASE

    gig = context.get("gig", None)
    if gig:
        the_from = gig.band.name
    else:
        the_from = DEFAULT_FROM_EMAIL_NAME

    the_from = f"{the_from}<{DEFAULT_FROM_EMAIL}>"

    with translation.override(recipient.language):
        text = render_to_string(template, context).strip()
    if text.startswith(SUBJECT):
        subject, text = [t.strip() for t in text[len(SUBJECT) :].split("\n", 1)]
    else:
        subject = DEFAULT_SUBJECT
    html = markdown(text, extensions=["nl2br"])

    message = mail.EmailMultiAlternatives(
        subject, text, from_email=the_from, to=[recipient.email_line], **kw
    )
    message.attach_alternative(html, "text/html")
    return message
