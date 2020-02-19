{% load i18n %}{% autoescape off %}
Subject: {% block subject %}{% endblock %}

{% block opening %}{% endblock %}

{{ gig.title }}
{% trans "Date" %}: {{ gig.date|date:"SHORT_DATE_FORMAT" }} ({{ gig.date|date:"D" }}){% if gig.enddate %} - {{ gig.enddate|date:"SHORT_DATE_FORMAT" }} ({{ gig.enddate|date:"D" }}){% endif %}
{% trans "Time" %}: {% if gig.calltime %}{{ gig.calltime|time:"TIME_FORMAT" }} ({% trans "Call Time" %}){% if gig.settime or gig.endtime %}, {% endif %}{% endif %}{% if gig.settime %}{{ gig.settime|time:"TIME_FORMAT" }} ({% trans "Set Time" %}){% if gig.endtime %}, {% endif %}{% endif %}{% if gig.endtime %}{{ gig.endtime|time:"TIME_FORMAT" }} ({% trans "End Time" %}){% endif %}
{% trans "Contact" %}: {{ contact_name }}
{% trans "Status" %}: {{ gig.status_string }}
{% if gig.details %}
{{ gig.details }}
{% endif %}{% if gig.setlist %}
{{ gig.setlist }}
{% endif %}
{% blocktrans %}If you **can** make it, [click here]({{ yes_url }}).

If you **can't** make it, [click here]({{ no_url }}).

If you **aren't sure** and want to be reminded in a few days, [click here]({{ snooze_url }}).{% endblocktrans %}
{% url 'gig-detail' gig.id as gig_url %}
{% blocktrans %}Gig info page is [here](https://gig-o-matic.com{{ gig_url }}).{% endblocktrans %}

{% blocktrans %}Thanks,
The Gig-o-Matic Team{% endblocktrans %}{% endautoescape %}
