import copy
from unittest.mock import patch

from django.test import override_settings, TestCase
from django.utils import translation
from go3 import settings

MISSING = "MISSING"
MISSING_TEMPLATES = copy.deepcopy(settings.TEMPLATES)
MISSING_TEMPLATES[0]["OPTIONS"]["string_if_invalid"] = f"{MISSING}: %s"

flag_missing_vars = override_settings(TEMPLATES=MISSING_TEMPLATES)


class TemplateTestCase(TestCase):

    def assertOK(self, response):
        self.assertEqual(response.status_code, 200)

    def assertPermissionDenied(self, response):
        self.assertEqual(response.status_code, 403)

    def assertRenderLanguage(self, lang, render_cmd="django.shortcuts.render"):
        test_case = self

        class LanguageReport(Exception):
            def __init__(self, lang):
                self.lang = lang

        def fake_render(*args, **kw):
            raise LanguageReport(translation.get_language())

        class RenderLanguageContextManager:

            def __enter__(self):
                self.patcher = patch(render_cmd, fake_render)
                self.patcher.start()

            def __exit__(self, exc_type, exc_value, tb):
                self.patcher.stop()
                if exc_type is None:
                    test_case.fail("Render code was not called")
                if isinstance(exc_value, LanguageReport):
                    if exc_value.lang != lang:
                        test_case.fail(
                            f"Language when render was called was {exc_value.lang}; expected to be {lang}"
                        )
                    return True
                return False  # Other errors will be raised

        return RenderLanguageContextManager()
