import copy

from django.test import override_settings
from go3 import settings

MISSING = 'MISSING'
MISSING_TEMPLATES = copy.deepcopy(settings.TEMPLATES)
MISSING_TEMPLATES[0]['OPTIONS']['string_if_invalid'] = f'{MISSING}: %s'

flag_missing_vars = override_settings(TEMPLATES=MISSING_TEMPLATES)
