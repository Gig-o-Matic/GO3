from django.db import models


class MOTD(models.Model):
    text = models.TextField(max_length=500, blank=True, null=True)
    updated = models.DateTimeField(auto_now= True)

