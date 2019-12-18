from django.db import models

class Band(models.Model):
    name = models.CharField(max_length=200)
    hometown = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class Assoc(models.Model):
    band = models.ForeignKey(Band, related_name="assocs", on_delete=models.CASCADE)
    member = models.ForeignKey("member.Member", verbose_name="member", related_name="assocs", on_delete=models.CASCADE)

    def __str__(self):
        return "{0} in {1}".format(self.member, self.band)

