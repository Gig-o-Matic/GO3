{% load i18n %}{% autoescape off %}
Subject: {% trans "Watched Gigs Alert From Gig-o-Matic" %}

{% blocktrans %}Hello!

Some plans you're watching have changed - see below

Thanks,
The Gig-o-Matic Team{% endblocktrans %}{% endautoescape %}

<br><br>

{% for band in data %}
{{band.0.name}}<br>
+++{{url_base}}+++
{% for gig in band.1 %}
{{ gig.0.date }} - <a href="{{url_base}}{% url 'gig-detail' pk=gig.0.id %}">{{gig.0.title}}</a><br>
<ul>
{% for plan in gig.1 %}
<li>{{plan.0}} is now {{plan.1}}
{% endfor %}
</ul>
<br>
{% endfor %}
<br><br>
{% endfor %}

<br><br>
{% blocktrans %}
You can stop watching gigs from your profile page.
{% endblocktrans %}