{% load i18n %}{% autoescape off %}
Subject: {% if new %}{% trans "Invitation to Join Gig-o-Matic" %}{% else %}{% trans "Gig-o-Matic New Band Invite" %}{% endif %}

{% url 'member-invite-accept' invite_id as url %}
{% blocktrans %}Hello,

As a member of {{ band_name }}, you have been invited to join the Gig-o-Matic to help manage your gigs.{% endblocktrans %}  {% if new %}{% blocktrans %}To sign up, you only need to create a password.

[Click here]({{url_base}}{{ url }}) to get started.{% endblocktrans %}{% else %}{% blocktrans %}[Click here]({{ url_base }}/{{ url }}) to associate your existing Gig-o-Matic account with {{ band_name }}.{% endblocktrans %}{% endif %}

{% blocktrans %}Thanks,
The Gig-o-Matic Administration Council{% endblocktrans %}{% endautoescape %}