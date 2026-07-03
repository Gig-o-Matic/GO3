from django.test import TestCase, Client
from django.urls import reverse
from freezegun import freeze_time
from datetime import datetime, timedelta
from member.models import Member

# Create your tests here.

class FirewallTests(TestCase):

    def test_ip_firewall(self):
        c = Client()
        c.force_login(Member.objects.create_user(email='super@b.c', is_superuser=True))
        _ = c.get("/firewall/firewall_on")
        _ = c.get("/firewall/reset_stats")

        response = c.get("/111")
        assert response.status_code==404
        response = c.get("/222")
        assert response.status_code==404
        response = c.get("/333") # third time should get permission denied
        assert response.status_code==403

        response = c.get("/444") # fourth time should get permission denied
        assert response.status_code==403

        with freeze_time(datetime.now()+timedelta(seconds=100)):
            response = c.get("/555") # 100 seconds in future should get permission denied
            assert response.status_code==403

        with freeze_time(datetime.now()+timedelta(seconds=600)):
            response = c.get("/666") # 600 seconds in future should get not found again
            assert response.status_code==404

    def test_clear_probation(self):
        c = Client()
        c.force_login(Member.objects.create_user(email='super@b.c', is_superuser=True))
        _ = c.get("/firewall/firewall_on")
        _ = c.get("/firewall/reset_stats")

        response = c.get('/xxx')
        assert response.status_code==404
        response = c.get(f"/xxx")
        assert response.status_code==404

        # if we don't send another until the future, we should come back 404 b/c the first
        # request won't count against us anymore.
        with freeze_time(datetime.now()+timedelta(seconds=601)):
            response = c.get(f"/xxx")
            assert response.status_code==404
