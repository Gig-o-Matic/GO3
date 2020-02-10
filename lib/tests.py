from unittest.mock import patch, mock_open

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings

from lib.email import send_mail_async, send_markdown_mail, DEFAULT_SUBJECT

class EmailTest(TestCase):

    def test_send_async(self):
        self.assertEqual(len(mail.outbox), 0)
        send_mail_async('Test Subject', 'Message', 'from@example.com', ['to@example.com'])
        self.assertEqual(len(mail.outbox), 1)

    @patch('builtins.open', mock_open(read_data='**Markdown**'))
    def test_markdown_mail(self):
        send_markdown_mail('test1', {}, ['to@example.com'])
        message = mail.outbox[0]
        self.assertIn('**Markdown**', message.body)
        self.assertEqual(len(message.alternatives), 1)
        self.assertEqual(message.alternatives[0][1], 'text/html')
        self.assertIn('<strong>Markdown</strong>', message.alternatives[0][0])

    @patch('builtins.open', mock_open(read_data='{{ key }}'))
    def test_markdown_template(self):
        send_markdown_mail('test2', {'key': 'value'}, ['to@example.com'])
        message = mail.outbox[0]
        self.assertIn('value', message.body)
        self.assertIn('value', message.alternatives[0][0])

    @patch('builtins.open', mock_open(read_data='Body'))
    def test_markdown_default_subject(self):
        send_markdown_mail('test3', {'key': 'value'}, ['to@example.com'])
        self.assertEqual(mail.outbox[0].subject, DEFAULT_SUBJECT)

    @patch('builtins.open', mock_open(read_data='Subject: Custom\nBody'))
    def test_markdown_subject(self):
        send_markdown_mail('test4', {'key': 'value'}, ['to@example.com'])
        self.assertEqual(mail.outbox[0].subject, 'Custom')
