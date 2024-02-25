import urllib.request
import random
import json
import datetime

names = []
with urllib.request.urlopen(
    "http://names.drycodes.com/100?nameOptions=boy_names&separator=space&format=json"
) as f:
    names = json.loads((f.read().decode("utf-8")))
with urllib.request.urlopen(
    "http://names.drycodes.com/100?nameOptions=girl_names&separator=space&format=json"
) as f:
    names += json.loads((f.read().decode("utf-8")))

# make a bunch of people
people = []
for i in range(0, 200):
    n = names[i]
    people.append(
        {
            "model": "member.member",
            "pk": 100 + i,
            "fields": {
                "email": f'{n.replace(" ","")}@foo.com',
                "username": n,
            },
        }
    )


band_names = []
b_prefix = ["The ", ""]
with urllib.request.urlopen(
    "http://names.drycodes.com/25?nameOptions=funnyWords&separator=space&format=json"
) as f:
    b_main = json.loads(f.read().decode("utf-8"))
b_type = [" Band", " Brass Band", " Barching Band", ""]

with urllib.request.urlopen(
    "http://names.drycodes.com/25?nameOptions=cities&separator=space&format=json"
) as f:
    cities = json.loads(f.read().decode("utf-8"))

while len(band_names) < 25:
    band = f"{random.choice(b_prefix)}{random.choice(b_main)}{random.choice(b_type)}"
    if not band in band_names:
        band_names.append(band)

# make a bunch of bands
bands = []
for i in range(0, len(band_names)):
    n = band_names[i]
    bands.append(
        {
            "model": "band.band",
            "pk": 100 + i,
            "fields": {
                "name": n,
                # "hometown": random.choice(cities),
                "creation_date": datetime.datetime.now(),
                "last_activity": datetime.datetime.now(),
            },
        }
    )

# now put members in bands
assocs = []
c = 10
for p in people:
    # put everybody in the first band
    assocs.append(
        {
            "model": "band.assoc",
            "pk": c,
            "fields": {
                "band": bands[0]["pk"],
                "member": p["pk"],
                "status": 1,
                "is_admin": False,
                "is_multisectional": False,
                "is_occasional": False,
                "color": 1,
                "email_me": True,
                "hide_from_schedule": False,
                "join_date": datetime.datetime.now(),
            },
        }
    )

    # now put in a few others

    otherbands = []
    while len(otherbands) < 3:
        b = random.choice(bands[1:])
        if not b["pk"] in otherbands:
            otherbands.append(b["pk"])

    for bpk in otherbands:
        c += 1
        assocs.append(
            {
                "model": "band.assoc",
                "pk": c,
                "fields": {
                    "band": bpk,
                    "member": p["pk"],
                    "status": 1,
                    "is_admin": False,
                    "is_multisectional": False,
                    "is_occasional": False,
                    "color": 1,
                    "email_me": True,
                    "hide_from_schedule": False,
                },
            }
        )

gigs = []
for i in range(0, 20):
    gigs.append(
        {
            "model": "gig.gig",
            "pk": 100 + i,
            "fields": {
                "title": f"Test Gig {i}",
                "band": bands[0]["pk"],
                "created_date": datetime.datetime.now(),
                "last_update": datetime.datetime.now(),
                "date": datetime.datetime.now()
                + datetime.timedelta(days=random.randrange(0, 30)),
            },
        }
    )

all = people + bands + assocs


def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.strftime("%Y-%m-%d")


print(json.dumps(all, default=myconverter))
test_json = json.dumps(all, default=myconverter)
with open("fixtures/testdata.json", "w") as outfile:
    outfile.write(test_json)

# print(json.dumps(all))
