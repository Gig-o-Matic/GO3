{% extends "email/gig.md" %}
{% load i18n %}

{% block subject %}{% blocktrans %}Gig Reminder: {{ gig.title }}{% endblocktrans %}{% endblock %}

{% block opening %}{% blocktrans with band_name=gig.band.name %}Hello! Just a reminder to weigh in on a gig for your band {{ band_name }}:{% endblocktrans %}{% endblock %}
