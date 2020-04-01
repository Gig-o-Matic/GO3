{% load i18n %}{% autoescape off %}
Subject: {% if new %}{% trans "Invitation to Join Gig-o-Matic" %}{% else %}{% trans "Gig-o-Matic New Band Invite" %}{% endif %}

{% url 'member-invite-accept' member.id as url %}
{% blocktrans with band_name=member.band.name %}Hello,

As a member of {{ band_name }}, you have been invited to join the Gig-o-Matic to help manage your gigs.{% endblocktrans %}  {% if new %}{% blocktrans %}To sign up, you only need to create a password.

[Click here](https://gig-o-matic.com{{ url }}) to get started.{% endblocktrans %}{% else %}{% blocktrans with band_name=member.band.name %}[Click here](https://gig-o-matic.com{{ url }}) to associate your existing Gig-o-Matic account with {{ band_name }}.{% endblocktrans %}{% endif %}

{% blocktrans %}Thanks,
The Gig-o-Matic Administration Council{% endblocktrans %}{% endautoescape %}
