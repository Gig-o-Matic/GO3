Subject: {{ gig_name }} RSVP

{{ responder_name }} has rsvp'ed {{ response }} to {{ gig_name }}!

Here's how everyone has responded so far:

{% for plan in plans %}
    {{ plan.member.display_name }}: {% include 'status_emoji.md' %}
{% endFor %}

Enjoy,
Team Gig-o-Matic