{% extends "email/gig.md" %}
{% load i18n %}

{% block subject %}{% blocktrans with gig.title as gig_title %}New Gig Series: {{ gig_title }}{% endblocktrans %}{% endblock %}

{% block opening %}{% blocktrans with band_name=gig.band.name %}Hello! A new series of gigs has been added to the Gig-o-Matic for your band {{ band_name }}:{% endblocktrans %}{% endblock %}

{% block gigdates %}
{% trans "First Date" %}: {{ dates|first|date:"SHORT_DATE_FORMAT" }} ({{ dates|first|date:"D" }})
{% trans "Last Date" %}: {{ dates|last|date:"SHORT_DATE_FORMAT" }} ({{ dates|last|date:"D" }})
{% trans "Call Time" %}: {{ gig.date|date:"TIME_FORMAT" }}{% if gig.setdate %}
{% trans "Set Time" %}: {{ gig.setdate|date:"TIME_FORMAT" }}{% endif %}{% if gig.enddate %}
{% trans "End Time" %}: {{ gig.enddate|date:"TIME_FORMAT" }}{% endif %}{% if gig.datenotes %}{% trans "Notes" %}: {{ gig.datenotes }}{% endif %}{% endblock gigdates %}

{% block answer %}

{% blocktrans %}Please check the gig-o-matic to weigh in on these gigs!{% endblocktrans %}
{% endblock answer %}