{% if plan.status == 0}
-
{% elif plan.status == 1}
🟢 Definitely
{% elif plan.status == 2}
🟢 Maybe
{% elif plan.status == 3}
? Don't know
{% elif plan.status == 4}
🟥 Probably not
{% elif plan.status == 5}
🟥 Definitely not
{% elif plan.status == 6}
❌ Not interested
{% endif %}