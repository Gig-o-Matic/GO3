from django.core import mail
from django.test import TestCase

from lib.email import send_messages_async

class EmailTest(TestCase):

    def test_send_messages_async(self):
        self.assertEqual(len(mail.outbox), 0)
        send_messages_async([mail.EmailMessage('Subject', 'Body', 'from@example.com', ['to@example.com'])])
        self.assertEqual(len(mail.outbox), 1)

    def test_send_many_messages_async(self):
        self.assertEqual(len(mail.outbox), 0)
        send_messages_async([mail.EmailMessage('Subject', 'Body', 'from@example.com', ['to@example.com'])] * 5)
        self.assertEqual(len(mail.outbox), 5)
