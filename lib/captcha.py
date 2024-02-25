"""
    This file is part of Gig-o-Matic

    Gig-o-Matic is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from go3.settings import env
import json
from urllib import request as urllib_request
from urllib import parse as urllib_parse


def get_captcha_site_key():
    return env("CAPTCHA_SITE_KEY", default="xyz")


def verify_captcha(request):

    captcha_token = request.POST.get("g-recaptcha-response", "")

    if captcha_token:
        verify_data = {
            "secret": env("CAPTCHA_SECRET_KEY", default="xyz"),
            "response": captcha_token,
            "remoteip": request.get_host(),
        }
        response = json.loads(
            urllib_request.urlopen(
                "https://www.google.com/recaptcha/api/siteverify",
                data=urllib_parse.urlencode(verify_data).encode("utf-8"),
            ).read()
        )
        if not (
            response["success"]
            and response["score"] > env("CAPTCHA_THRESHOLD", default=0)
        ):
            return False
    else:
        return False

    return True
