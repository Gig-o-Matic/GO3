{% load i18n %}{% autoescape off %}
Subject: {% trans "New joiner for" %} {{ band.name }}

{% trans "Hi there!" %} {{ joiner.display_name }} {% trans "has requested to join" %} {{ band.name }}.

{% blocktrans %}Accept or reject the invitation on your Band's page:{% endblocktrans %}
{{ url_base }}{% url 'band-detail' pk=band.id %}#pending-members

{% blocktrans %}
Enjoy,
Team Gig-o-Matic
{% endblocktrans %}
{% endautoescape %}