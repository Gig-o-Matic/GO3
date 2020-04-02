{% load i18n %}{% autoescape off %}
Subject: {% trans "Confirm your Email to Join Gig-o-Matic" %}

{% url 'member-invite-accept' member.id as url %}
{% blocktrans %}Hello!

You have registered to join Gig-o-Matic - click the link below to confirm your email and finish the sign-up process.

[Confirm email](https://gig-o-matic.com{{ url }})

Thanks,
The Gig-o-Matic Team{% endblocktrans %}{% endautoescape %}
