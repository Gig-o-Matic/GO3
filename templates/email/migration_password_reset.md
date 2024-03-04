{% load i18n %}{% autoescape off %}
Subject: {{ band.name }} {% trans "is moving to the new Gig-o-Matic!" %}

{% block reset_link %}
{{ protocol }}://{{ domain }}{% url 'password_reset_confirm' uidb64=uid token=token %}
{% endblock %}

{% blocktrans %}Hello{% endblocktrans %} {{ member.username }},

{% blocktrans %}Gig-o-Matic is evolving, and your band is evolving with it. The next generation of Gig-O is now live at{% endblocktrans %} {{ protocol }}://{{ domain }}

{% blocktrans %}
Your band membership is being copied to the new site, but you'll need to set a new password to gain access.
{% endblocktrans %}

[{% blocktrans %}Click here to set a new password{% endblocktrans %}]({{ reset_link }})



{% blocktrans %}Thanks,
The Gig-o-Matic Administration Council{% endblocktrans %}{% endautoescape %}