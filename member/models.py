from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from band.models import Band, Assoc
from django.utils.translation import gettext_lazy as _

class MemberManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email, and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None,  **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None,  **extra_fields):
        """
        Creates and saves a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


# a 1-1 link to user model
# https://simpleisbetterthancomplex.com/tutorial/2016/07/22/how-to-extend-django-user-model.html#onetoone


class Member(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)

    username = models.CharField(max_length=200)
    nickname = models.CharField(max_length=100, blank=True )
    phone = models.CharField(max_length=100, blank=True)
    statement = models.CharField(max_length=200, blank=True)
    seen_motd_time = models.DateTimeField(null=True, blank=True, default=None)
    seen_welcome = models.BooleanField(default=False)
    show_long_agenda = models.BooleanField(default=True)
    # pending_change_email = ndb.TextProperty(default='', indexed=False)
    images = models.TextField(max_length=500, blank=True)

    # flag to determine whether to recompute calendar feed
    cal_feed_dirty = models.BooleanField(default=True)

    @property
    def display_name(self):
        if self.nickname:
            return self.nickname
        elif self.username:
            return self.username
        else:
            return self.email

    @property
    def member_name(self):
        return self.username if self.username else self.email

    objects = MemberManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        permissions = (
            ("beta_tester", "Is A Beta Tester"),
        )
        verbose_name = _('member')
        verbose_name_plural = _('members')

    def __str__(self):
        return '{0}'.format(self.email)


class MemberPreferences(models.Model):
    """ class to hold user preferences """
    member = models.OneToOneField(Member, related_name='preferences', on_delete=models.CASCADE)

    hide_canceled_gigs = models.BooleanField(default=False)
    locale = models.CharField(max_length=200, default='en')
    share_profile = models.BooleanField(default=True)
    share_email = models.BooleanField(default=False)
    calendar_show_only_confirmed = models.BooleanField(default=True)
    calendar_show_only_committed = models.BooleanField(default=True)
    default_view = models.IntegerField(default=0) # 0 = agenda, 1 = calendar, 2 = grid
    agenda_show_time = models.BooleanField(default=False)


# signals to make sure a set of preferences is created for every user
@receiver(post_save, sender=Member)
def create_user_preferences(sender, instance, created, **kwargs):
    if created:
        MemberPreferences.objects.create(member=instance)

@receiver(post_save, sender=Member)
def save_user_preferences(sender, instance, **kwargs):
    instance.preferences.save()

