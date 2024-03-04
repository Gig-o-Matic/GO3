{% load i18n %}{% autoescape off %}


{% blocktrans %}Hello{% endblocktrans %} {{ member.username }},

{% blocktrans %}Gig-o-Matic is evolving, and your band is evolving with it. The next generation of Gig-O is now live at{% endblocktrans %} {{ protocol }}://{{ domain }}

{% blocktrans %}
Your band membership is being copied to the new site, but you'll need to set a new password to gain access.
{% endblocktrans %}

[{% blocktrans %}Click here to set a new password{% endblocktrans %}]({{ protocol }}://{{ domain }}{% url 'password_reset_confirm' uidb64=uid token=token %})

Link not working? Copy & paste this into your web browser: {{ protocol }}://{{ domain }}{% url 'password_reset_confirm' uidb64=uid token=token %}

{% blocktrans %}Thanks,
The Gig-o-Matic Administration Council{% endblocktrans %}{% endautoescape %}