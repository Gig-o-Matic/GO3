from django.core import mail
from django.test import TestCase
from django.urls import reverse
from lib.template_test import MISSING, flag_missing_vars


class BandRequestTest(TestCase):

    @flag_missing_vars
    def test_band_request(self):
        post_body = {
            "email": "new@example.com",
            "name": "New Person",
            "message": "I have a cool new band!",
        }
        response = self.client.post(reverse("help-band-request"), post_body)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Gig-o-Matic New Band Request")
        for v in post_body.values():
            self.assertIn(v, message.body)
        self.assertNotIn(MISSING, message.body)
