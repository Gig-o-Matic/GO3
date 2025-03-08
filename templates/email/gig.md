{% load i18n %}{% autoescape off %}
{% load tz %}{% localtime on %}
Subject: {% block subject %}{% endblock %}

{% block opening %}{% endblock %}

{% trans "Gig"%}: {{ gig.title }}

{% block gigdates %}
{% if gig.is_full_day %}
{% trans "Date" %}: {{ gig.date|date:"SHORT_DATE_FORMAT" }} ({{ gig.date|date:"D" }}){% if gig.enddate %} - {{ gig.enddate|date:"SHORT_DATE_FORMAT" }} ({{ gig.enddate|date:"D" }}){% endif %}
{% else %}
{% trans "Date" %}: {{ gig.date|date:"SHORT_DATE_FORMAT" }} ({{ gig.date|date:"D" }})
{% trans "Call Time" %}: {{ gig.date|date:"TIME_FORMAT" }}{% if gig.setdate %}
{% trans "Set Time" %}: {{ gig.setdate|date:"TIME_FORMAT" }}{% endif %}{% if gig.enddate %}
{% trans "End Time" %}: {{ gig.enddate|date:"TIME_FORMAT" }}{% endif %}
{% endif %}{% if gig.datenotes %}{% trans "Notes" %}: {{ gig.datenotes }}{% endif %}{% endblock gigdates %}

{% if gig.address %}
{% trans "Address" %}: {{ gig.address }}
{% endif %}

{% trans "Contact" %}: {{ contact_name }}
{% trans "Status" %}: {{ gig.status_string }}
{% if gig.details %}
{{ gig.details }}
{% endif %}{% if gig.setlist %}
{{ gig.setlist }}
{% endif %}{% block answer %}{% if status != NO_PLAN and status != DONT_KNOW %}
{% blocktrans %}Your current status is "{{ status_label }}".  If that is still correct, you need not take any action.{% endblocktrans %}
{% endif %}{% if status != DEFINITELY %}{% url 'gig-answer' plan.id DEFINITELY as yes_url %}
{% blocktrans %}If you **can** make it, [click here]({{url_base}}{{ yes_url }}).{% endblocktrans %}
{% endif %}{% if status != CANT_DO_IT %}{% url 'gig-answer' plan.id CANT_DO_IT as no_url %}
{% blocktrans %}If you **can't** make it, [click here]({{url_base}}{{ no_url }}).{% endblocktrans %}
{% endif %}{% url 'gig-answer' plan.id DONT_KNOW as snooze_url %}
{% blocktrans %}If you **aren't sure** and want to be reminded in a few days, [click here]({{url_base}}{{ snooze_url }}).{% endblocktrans %}
{% url 'gig-detail' gig.id as gig_url %}
{% blocktrans %}Gig info page is [here]({{url_base}}{{ gig_url }}).{% endblocktrans %}{% endblock answer %}

{% blocktrans %}Thanks,
The Gig-o-Matic Team{% endblocktrans %}{% endlocaltime %}{% endautoescape %}
