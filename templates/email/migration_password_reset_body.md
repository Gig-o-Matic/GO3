{% load i18n %}{% autoescape off %}


{% blocktrans %}Hello{% endblocktrans %} {{ member.username }},

{% blocktrans %}Gig-o-Matic is evolving, and your band is evolving with it. The next generation of Gig-O is now live at{% endblocktrans %} {{ protocol }}://{{ domain }}

{% blocktrans %}
Your Gig-O account is being upgraded, so you'll need to set a new password to gain access.
{% endblocktrans %}

{% blocktrans %}Click here to set a new password:{% endblocktrans %}
{{ protocol }}://{{ domain }}{% url 'password_reset_confirm' uidb64=uid token=token %}

{% blocktrans %}Link not clickable? Copy & paste it into your web browser.{% endblocktrans %}

{% blocktrans %}
Thanks,
The Gig-o-Matic Administration Council
{% endblocktrans %}
{% endautoescape %}