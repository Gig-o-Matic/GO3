{% load i18n %}{% autoescape off %}
Subject: Gig-o-Matic Email Confirmation

{% url 'member-confirm-email' confirmation_id as url %}
{% blocktrans %}Hello,

Someone has requested to use this email address for a member of the Gig-o-Matic{% endblocktrans %}

{% blocktrans %}[Click here]({{url_base}}{{ url }}) to confirm the address.{% endblocktrans %}

{% blocktrans %}Thanks,
The Gig-o-Matic Administration Council{% endblocktrans %}{% endautoescape %}
