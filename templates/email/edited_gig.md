{% extends "email/gig.md" %}
{% load i18n %}

{% block subject %}{% blocktrans with gig.title as gig_title %}Gig Edit ({{ change_string }}) {{ gig_title }}{% endblocktrans %}{% endblock %}

{% block opening %}{% blocktrans with band_name=gig.band.name %}Hello! A gig has been edited in the Gig-o-Matic for your band {{ band_name }}:{% endblocktrans %}

{% trans "EDITED" %}: {{ change_string }}{% endblock %}
