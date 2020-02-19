{% extends "email/gig.md" %}
{% load i18n %}

{% block subject %}{% blocktrans %}New Gig: {{ gig.title }}{% endblocktrans %}{% endblock %}

{% block opening %}{% blocktrans with band_name=gig.band.name %}Hello! A new gig has been added to the Gig-o-Matic for your band {{ band_name }}:{% endblocktrans %}{% endblock %}
