from django.db.models import DateTimeField
from pytz import utc

class DateTimeWithoutTimezoneField(DateTimeField):
    def db_type(self, connection):
        return 'timestamp'
    
    def get_prep_value(self, value):
        # Fake UTC timezone to mollify the parent class
        # Since we are not storing timezones, this will be thrown away
        if value:
            value = value.replace(tzinfo=utc)
        return super().get_prep_value(value)
