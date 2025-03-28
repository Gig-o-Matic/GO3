{% load i18n %}{% autoescape off %}
Subject: {% trans "Watched Gigs Alert From Gig-o-Matic" %}

{% blocktrans %}Hello!

Some plans you're watching have changed - see below

Thanks,
The Gig-o-Matic Team{% endblocktrans %}{% endautoescape %}

<br><br>
{{data}}
{% for band in data %}
{{band.0.name}}<br>

{% for gig in band.1 %}
{{ gig.0.date }} - {{gig.0.title}}<br>
<ul>
{% for plan in gig.1 %}
<li>{{plan.0}} is now {{plan.1}}
{% endfor %}
</ul>
<br>
{% endfor %}
<br><br>
{% endfor %}

<ul>
{% for p in plans %}
<li>{{p.0.band.name}}: {{p.0.title}} - {{p.1.display_name}} ({{p.1.email}}) is now {{p.2}}</li>
{% endfor %}
</ul>
<br><br>
{% blocktrans %}
You can stop watching gigs from your profile page.
{% endblocktrans %}