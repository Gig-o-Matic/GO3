{% load i18n %}{% autoescape off %}
Subject: {% block subject %}{% endblock %}

{% block opening %}{% endblock %}

{{ gig.title }}{% if single_day %}
{% trans "Date" %}: {{ gig.date|date:"SHORT_DATE_FORMAT" }} ({{ gig.date|date:"D" }})
{% trans "Time" %}: {{ gig.date|time:"TIME_FORMAT" }} ({% trans "Call Time" %}){% if gig.setdate or gig.enddate %}, {% endif %}{% if gig.setdate %}{{ gig.setdate|time:"TIME_FORMAT" }} ({% trans "Set Time" %}){% if gig.enddate %}, {% endif %}{% endif %}{% if gig.enddate %}{{ gig.enddate|time:"TIME_FORMAT" }} ({% trans "End Time" %}){% endif %}
{% else %}
{% trans "Call Time" %}: {{ gig.date|date:"SHORT_DATETIME_FORMAT" }} ({{ gig.date|date:"D" }}){% if gig.setdate %}
{% trans "Set Time" %}: {{ gig.setdate|date:"SHORT_DATETIME_FORMAT" }} ({{ gig.setdate|date:"D" }}){% endif %}{% if gig.enddate %}
{% trans "End Time" %}: {{ gig.enddate|date:"SHORT_DATETIME_FORMAT" }} ({{ gig.enddate|date:"D" }}){% endif %}
{% endif %}{% trans "Contact" %}: {{ contact_name }}
{% trans "Status" %}: {{ gig.status_string }}
{% if gig.details %}
{{ gig.details }}
{% endif %}{% if gig.setlist %}
{{ gig.setlist }}
{% endif %}{% if status != NO_PLAN and status != DONT_KNOW %}
{% blocktrans %}Your current status is "{{ status_label }}".  If that is still correct, you need not take any action.{% endblocktrans %}
{% endif %}{% if status != DEFINITELY %}{% url 'gig-answer' plan.id DEFINITELY as yes_url %}
{% blocktrans %}If you **can** make it, [click here]({{url_base}}{{ yes_url }}).{% endblocktrans %}
{% endif %}{% if status != CANT_DO_IT %}{% url 'gig-answer' plan.id CANT_DO_IT as no_url %}
{% blocktrans %}If you **can't** make it, [click here]({{url_base}}{{ no_url }}).{% endblocktrans %}
{% endif %}{% url 'gig-answer' plan.id DONT_KNOW as snooze_url %}
{% blocktrans %}If you **aren't sure** and want to be reminded in a few days, [click here]({{url_base}}{{ snooze_url }}).{% endblocktrans %}
{% url 'gig-detail' gig.id as gig_url %}
{% blocktrans %}Gig info page is [here]({{url_base}}{{ gig_url }}).{% endblocktrans %}

{% blocktrans %}Thanks,
The Gig-o-Matic Team{% endblocktrans %}{% endautoescape %}
