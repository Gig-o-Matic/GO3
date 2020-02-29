{% extends "email/gig.md" %}
{% load i18n %}

{% block subject %}{% blocktrans with gig.title as gig_title %}Gig Edit ({{ changes_title }}) {{ gig_title }}{% endblocktrans %}{% endblock %}

{% block opening %}{% blocktrans with band_name=gig.band.name %}Hello! A gig has been edited in the Gig-o-Matic for your band {{ band_name }}:{% endblocktrans %}

{% trans "EDITED" %}{% for change, new, old in changes %}
{{ change }}: {{ new }} {% if old %}{% blocktrans with old_str=old %}(was {{ old_str }}){% endblocktrans %}{% endif %}{% endfor %}{% endblock %}
