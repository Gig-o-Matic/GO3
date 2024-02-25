# -*- coding: UTF-8 -*-
# read the output from an appengine backup and parse to CSV files


# Make sure App Engine APK is available
import sys, os

sys.path.append("/usr/local/google_appengine")
from google.appengine.api.files import records
from google.appengine.datastore import entity_pb
from google.appengine.api import datastore
import progressbar
import random
import datetime
from pytz import timezone as tzone, utc
from dateutil.parser import parse

DEBUG = False

# order is important
objects = [
    "Band",
    "Section",
    "Member",
    "Assoc",
    "Gig",
    "Comment",
    "Plan",
]
count = {}

columns = {
    "Band": [
        "show_in_nav",
        "hometown",
        "member_links",
        "new_member_message",
        "timezone",
        "anyone_can_create_gigs",
        "condensed_name",
        "share_gigs",
        "band_cal_feed_dirty",
        "rss_feed",
        "pub_cal_feed_dirty",
        "shortname",
        "enable_forum",
        "website",
        "description",
        "send_updates_by_default",
        "thumbnail_img",
        "anyone_can_manage_gigs",
        "simple_planning",
        "plan_feedback",
        "name",
        "created",
        "lower_name",
        "images",
        "sections",
    ],
    "Section": ["name"],
    "Member": [
        "preferences.default_view",
        "email_address",
        "preferences.email_new_gig",
        "show_long_agenda",
        "display_name",
        "pending_change_email",
        "preferences.locale",
        "is_superuser",
        "seen_motd_time",
        "statement",
        "preferences.share_email",
        "is_betatester",
        "seen_motd",
        "updated",
        "preferences.agenda_show_time",
        "phone",
        "is_band_editor",
        "seen_welcome",
        "verified",
        "nickname",
        "name",
        "created",
        "preferences.calendar_show_only_committed",
        "preferences.share_profile",
        "preferences.calendar_show_only_confirmed",
        "preferences.hide_canceled_gigs",
        "created",
    ],
    "Gig": [
        "creator",
        "is_archived",
        "is_in_trash",
        "trueenddate",
        "dress",
        "archive_id",
        "trashed_date",
        "is_canceled",
        "is_confirmed",
        "title",
        "details",
        "default_to_attending",
        "leader",
        "status",
        "comment_id",
        "hide_from_calendar",
        "calltime",
        "paid",
        "address",
        "date",
        "invite_occasionals",
        "endtime",
        "is_private",
        "was_reminded",
        "enddate",
        "rss_description",
        "setlist",
        "contact",
        "settime",
        "created_date",
        "postgig",
    ],
    "Assoc": [
        "is_occasional",
        "hide_from_schedule",
        "is_confirmed",
        "created",
        "color",
        "is_multisectional",
        "default_section_index",
        "default_section",
        "is_invited",
        "member",
        "band",
        "is_band_admin",
        "email_me",
        "member_name",
    ],
    "Plan": ["comment", "section", "feedback_value", "value", "member"],
    "Comment": ["member", "comment", "created_date"],
}

mappings = {}
assocs = {}
gigs = {}
band_sections = {}
band_timezones = {}

DATA_DIRECTORY = "export"
DELIMITER = "\t"


def set_up_outputs():
    outs = {}
    for o in objects:
        outs[o] = open("{}.json".format(o), "w")
        outs[o].write("[\n")
    return outs


def close_outputs(outs):
    for c in outs:
        outs[c].write("]")
        outs[c].close()


def make_id(entity_type, key):
    if not entity_type in mappings:
        mappings[entity_type] = {}
    id = len(mappings[entity_type]) + 100
    mappings[entity_type][key] = id
    return id


def key_to_str(key):
    return key.__str__()


def find_id(entity_type, key):
    val = mappings[entity_type].get(key)
    if val is None and DEBUG:
        val = 999
    return val


def store_assoc(band_id, member_id, assoc_id):
    if not band_id in assocs:
        assocs[band_id] = {}
    assocs[band_id][member_id] = assoc_id


def find_assoc(band_id, member_id):
    if not band_id in assocs:
        return None
    if not member_id in assocs[band_id]:
        return None
    return assocs[band_id][member_id]


def store_gig_band(gig_id, band_id):
    gigs[gig_id] = band_id


def find_gig_band(gig_id):
    return gigs[gig_id]


def save_band_sections(band_id, sections):
    band_sections[band_id] = sections


def find_band_sections(band_id):
    return band_sections[band_id]


def save_band_timezone(band_id, timezone):
    band_timezones[band_id] = timezone


def find_band_timezone(band_id):
    return band_timezones[band_id]


def get_key(entity):
    key = '"{0}"'.format(key_to_str(entity.key()))  # key
    parent = '"{0}"'.format(key_to_str(entity.parent()))  # parent
    return key[1:-1], parent[1:-1]


def enc(string):
    the_str = string.encode("utf-8") if string else ""
    the_str = the_str.replace("\\", "\\\\")
    the_str = the_str.replace('"', '\\"')
    the_str = the_str.replace("\r\n", "\\n")
    the_str = the_str.replace("\n", "\\n")
    the_str = the_str.replace("	", " ")
    return the_str


def tf(it):
    return "true" if it else "false"


def date(d):
    return date.isoformat()


# 'show_in_nav', 'hometown', 'member_links', 'new_member_message','timezone', 'anyone_can_create_gigs',
# 'condensed_name', 'share_gigs', 'band_cal_feed_dirty', 'rss_feed', 'pub_cal_feed_dirty', 'shortname',
# 'enable_forum', 'website', 'description', 'send_updates_by_default', 'thumbnail_img', 'anyone_can_manage_gigs',
# 'simple_planning', 'plan_feedback', 'name', 'created', 'lower_name'
def make_band_object(entity):
    key, parent = get_key(entity)

    id = make_id("Band", key)

    sections = entity.get("sections", [])
    save_band_sections(id, [str(s) for s in sections])
    save_band_timezone(id, entity["timezone"])

    return """{{
    "model": "band.band",
    "pk": {0},
    "fields": {{
        "name": "{1}",
        "hometown": "{2}",
        "shortname": "{3}",
        "website": "{4}",
        "description": "{5}",
        "images": "{6}",
        "member_links": "{7}",
        "thumbnail_img": "{8}",
        "timezone": "{9}",
        "new_member_message": "{10}",
        "anyone_can_manage_gigs": {11},
        "anyone_can_create_gigs": {12},
        "send_updates_by_default": {13},
        "simple_planning": {14},
        "plan_feedback": "{15}",
        "creation_date": "{16}",
        "last_activity": "{17}",
        "default_language": "en-us"
    }}
}},\n""".format(
        id,
        enc(entity["name"]),
        enc(entity["hometown"]),
        enc(entity["shortname"]),
        entity["website"],
        enc(entity["description"]),
        entity.get("images"),
        enc(entity["member_links"]),
        entity["thumbnail_img"],
        entity["timezone"],
        enc(entity.get("new_member_message")),
        tf(entity["anyone_can_manage_gigs"]),
        tf(entity.get("anyone_can_create_gigs")),
        tf(entity["send_updates_by_default"]),
        tf(entity["simple_planning"]),
        enc(entity["plan_feedback"]),
        entity["created"].strftime("%Y-%m-%d"),
        entity["created"],
    )


#    'Section': ['name'],
def make_section_object(entity):
    key, parent = get_key(entity)

    id = make_id("Section", key)
    parent_id = find_id("Band", parent)

    # figure out the index of this section
    band_sections = find_band_sections(parent_id)

    try:
        idx = band_sections.index(key)
    except ValueError:
        # section that doesn't seem to belong to a band properly - weird
        return ""

    return """{{
        "model": "band.section",
        "pk": {0},
        "fields": {{
            "name": "{1}",
            "band": {2},
            "order": {3}
        }}
}},\n""".format(
        id, entity["name"].encode("utf-8"), parent_id, idx
    )


# 'Member': ['preferences.default_view','email_address','preferences.email_new_gig','show_long_agenda','display_name',
#             'pending_change_email', 'preferences.locale','is_superuser','seen_motd_time','statement','preferences.share_email',
#             'is_betatester','seen_motd','updated','preferences.agenda_show_time','phone','is_band_editor','seen_welcome',
#             'verified','nickname','name','created', 'preferences.calendar_show_only_committed', 'preferences.share_profile',
#             'preferences.calendar_show_only_confirmed', 'preferences.hide_canceled_gigs','created'],
def make_member_object(entity):
    key, parent = get_key(entity)
    id = make_id("Member", key)

    statement = enc(entity["statement"])
    if not statement or statement == "None":
        statement = ""

    member_obj = """{{
        "model": "member.member",
        "pk": {0},
        "fields": {{
            "email": "{1}",
            "username": "{2}",
            "nickname": "{3}",
            "phone": "{4}",
            "statement": "{5}",
            "status": {6}
    }}
}},\n""".format(
        id,
        entity["email_address"],
        enc(entity["name"]),
        enc(entity["nickname"]),
        enc(entity["phone"]),
        statement,
        0,  # active
    )

    pref_obj = """{{
        "model": "member.memberpreferences",
        "fields": {{
            "member": {1},
            "hide_canceled_gigs": {2},
            "language": "{3}",
            "share_profile": {4},
            "share_email": {5},
            "calendar_show_only_confirmed": {6},
            "calendar_show_only_committed": {7},
            "agenda_show_time": {8},
            "default_view": {9}
    }}
}},\n""".format(
        id,  # we'll use the same pk as the member object we're associated with
        id,  # member id
        tf(entity["preferences.hide_canceled_gigs"]),
        entity["preferences.locale"],
        tf(entity["preferences.share_profile"]),
        tf(entity["preferences.share_email"]),
        tf(entity["preferences.calendar_show_only_confirmed"]),
        tf(entity["preferences.calendar_show_only_committed"]),
        tf(entity["preferences.agenda_show_time"]),
        entity["preferences.default_view"],
    )

    return "{0}\n{1}".format(member_obj, pref_obj)


# 'is_occasional', 'hide_from_schedule', 'is_confirmed', 'created', 'color', 'is_multisectional', 'default_section_index',
#               'default_section','is_invited', 'member','band','is_band_admin','email_me','member_name'
def make_assoc_object(entity):
    key, parent = get_key(entity)
    id = make_id("Assoc", key)

    member_id = find_id("Member", key_to_str(entity["member"]))
    band_id = find_id("Band", key_to_str(entity["band"]))
    status = 1 if entity["is_confirmed"] else 2 if entity["is_invited"] else 0

    join_date = entity["created"] if "created" in entity else None
    if join_date is None:
        join_date = "2021-01-01"
    elif type(join_date) == datetime.datetime:
        join_date = join_date.strftime("%Y-%m-%d")

    store_assoc(band_id, member_id, id)

    default_section = find_id("Section", key_to_str(entity["default_section"]))
    if not default_section:
        default_section = ""
    else:
        default_section = '"default_section": {0},'.format(default_section)

    return """{{
        "model": "band.assoc",
        "pk": {0},
        "fields": {{
            "band": {1},
            "member": {2},
            "status": {3},
            {4}
            "is_admin": {5},
            "is_occasional": {6},
            "join_date": "{7}",
            "is_multisectional": {8},
            "color": {9},
            "email_me": {10},
            "hide_from_schedule": {11}
        }}
}},\n""".format(
        id,
        band_id,
        member_id,
        status,
        default_section,
        tf(entity["is_band_admin"]),
        tf(entity["is_occasional"]),
        join_date,
        tf(entity["is_multisectional"]),
        entity["color"],
        tf(entity["email_me"]),
        tf(entity["hide_from_schedule"]),
    )


# 'Gig': ['creator','is_archived','is_in_trash','trueenddate','dress','archive_id','trashed_date',
#         'is_canceled','is_confirmed','title','details','default_to_attending', 'leader',
#         'status', 'comment_id', 'hide_from_calendar', 'calltime', 'paid', 'address', 'date',
#         'invite_occasionals', 'endtime', 'is_private', 'was_reminded', 'enddate', 'rss_description',
#         'setlist', 'contact', 'settime', 'created_date', 'postgig'],
def make_gig_object(entity):

    key, parent = get_key(entity)
    id = make_id("Gig", key)

    parent_id = find_id("Band", parent)

    store_gig_band(id, parent_id)

    tz = find_band_timezone(parent_id)

    def parsetime(d):
        if type(d) is datetime.datetime:
            return d, ""
        p_d = None
        datenotes = ""
        if d:
            try:
                p_d = parse(d)
            except ValueError:
                # can't parse it, so call this the notes
                datenotes = d

        return p_d, datenotes

    created_date = datetime.datetime.now()
    if "created_date" in entity:
        if entity["created_date"]:
            created_date = entity["created_date"]
    created_date = created_date.replace(tzinfo=tzone(tz))

    # deal with dates. GO2 has date, end date, and times for call, set, and end
    # we want datetimes for date, setdate, and enddate
    e_calltime = entity.get("calltime", None)
    e_settime = entity.get("settime", None)
    e_endtime = entity.get("endtime", None)
    e_date = entity.get("date", None)
    e_enddate = entity.get("enddate", None)

    # print(e_calltime, e_settime, e_endtime, e_date, e_enddate)

    pe_calltime, dn1 = parsetime(e_calltime)
    pe_settime, dn2 = parsetime(e_settime)
    pe_endtime, dn3 = parsetime(e_endtime)

    if pe_settime is None:
        pe_settime = datetime.time(hour=0, minute=0)

    if pe_calltime is None:
        pe_calltime = pe_settime

    if pe_endtime is None:
        pe_endtime = pe_settime

    date = e_date.replace(hour=pe_calltime.hour, minute=pe_calltime.minute)
    setdate = e_date.replace(hour=pe_settime.hour, minute=pe_settime.minute)

    if e_enddate:
        enddate = e_enddate.replace(hour=pe_endtime.hour, minute=pe_endtime.minute)
    else:
        enddate = e_date.replace(hour=pe_endtime.hour, minute=pe_endtime.minute)

    datenotes = " ".join([dn1, dn2, dn3]).strip()

    date = date.replace(tzinfo=tzone(tz))
    setdate = setdate.replace(tzinfo=tzone(tz))
    enddate = enddate.replace(tzinfo=tzone(tz))

    trashed_date, note = parsetime(entity.get("trashed_date", None))
    if not trashed_date:
        trashed_date = created_date
    else:
        trashed_date = trashed_date.replace(tzinfo=tzone(tz))

    enddate = enddate.isoformat()
    date = date.isoformat()
    setdate = setdate.isoformat()
    trashed_date = trashed_date.isoformat()
    created_date = created_date.isoformat()

    return """{{
        "model": "gig.gig",
        "pk": {0},
        "fields": {{
            "band": {1}, 
            "title": "{2}",
            "details": "{3}",
            "created_date": "{4}",
            "last_update": "2021-01-01",
            "date": "{5}",
            "address": "{6}",
            "status": {7},
            "is_archived": {8},
            "is_private": {9},
            "creator": {10},
            "invite_occasionals": {11},
            "was_reminded": {12},
            "hide_from_calendar": {13},
            "default_to_attending": {14},
            "trashed_date": "{15}",
            "contact": {16},
            "setlist": "{17}",
            "setdate": "{18}",
            "enddate": "{19}",
            "dress": "{20}",
            "paid": "{21}",
            "postgig": "{22}",
            "leader": {23},
            "datenotes": "{24}"
        }}
}},\n""".format(
        id,
        parent_id,
        enc(entity["title"]),
        enc(entity["details"]),
        created_date,
        date,
        enc(entity.get("address", None)),
        entity["status"],
        tf(entity["is_archived"]),
        tf(entity.get("is_private", None)),
        None,
        tf(entity.get("invite_occasionals", None)),
        tf(entity.get("was_reminded", None)),
        tf(entity.get("hide_from_calendar", None)),
        tf(entity.get("default_to_attending", False)),
        trashed_date,
        find_id("Member", key_to_str(entity["contact"])),
        enc(entity["setlist"]),
        setdate,
        enddate,
        enc(entity.get("dress", None)),
        enc(entity.get("paid", None)),
        enc(entity.get("postgig", None)),
        "null",  # enc(entity['leader'] if 'leader' in entity else None),
        enc(datenotes),
    )


# 'comment', 'section', 'feedback_value', 'value', 'member'
def make_plan_object(entity):
    key, parent = get_key(entity)
    id = make_id("Plan", key)

    parent_id = find_id("Gig", parent)
    member_id = find_id("Member", key_to_str(entity["member"]))

    if parent_id is None:
        # gig was deleted but not the plan - weird
        return None

    band_id = find_gig_band(parent_id)

    if member_id is None:
        # member deleted at some point but the plan wasn't - weird
        return None

    assoc_id = find_assoc(band_id, member_id)

    if assoc_id is None:
        # super weird
        return None

    section_id = find_id("Section", entity["section"])

    tz = find_band_timezone(find_gig_band(parent_id))
    mod_date = datetime.datetime.now()
    mod_date = mod_date.replace(tzinfo=tzone(tz))

    return """{{
        "model": "gig.plan",
        "pk": {0},
        "fields": {{
            "gig": {1}, 
            "assoc": {2},
            "status": {3},
            "feedback_value": {4},
            "comment": "{5}",
            "section": {6},
            "plan_section": {7},
            "last_update": "{8}"
        }}   
}},\n""".format(
        id,
        parent_id,
        assoc_id,
        entity["value"],
        entity.get("feedback_value", None),
        enc(entity.get("comment", ""))[:200],
        section_id,
        section_id,
        mod_date,
    )


def make_comment_object(entity):
    key, parent = get_key(entity)
    id = make_id("Comment", key)

    parent_id = find_id("Gig", parent)
    member_id = find_id("Member", key_to_str(entity["member"]))

    if member_id is None:
        # member deleted at some point but the plan wasn't - weird
        return None

    tz = find_band_timezone(find_gig_band(parent_id))

    created_date = datetime.datetime.now()
    if "created_date" in entity:
        if entity["created_date"]:
            created_date = entity["created_date"]
    created_date = created_date.replace(tzinfo=tzone(tz))

    return """{{
        "model": "gig.gigcomment",
        "pk": {0},
        "fields": {{
            "gig": {1}, 
            "member": {2},
            "text": "{3}",
            "created_date": "{4}"
        }}   
}},\n""".format(
        id, parent_id, member_id, enc(entity["comment"]), created_date
    )


def write_object(outs, the_type, entity):

    obj = {
        "Band": make_band_object,
        "Section": make_section_object,
        "Member": make_member_object,
        "Assoc": make_assoc_object,
        "Gig": make_gig_object,
        "Plan": make_plan_object,
        "Comment": make_comment_object,
    }[the_type](entity)
    f = outs[the_type]
    if obj:
        # last minute replacement - sheesh
        obj = obj.replace(': "None"', ": null")
        obj = obj.replace(": None", ": null")
        f.write(obj)
        f.write("\n")


def readfile(f, otype, outs):
    raw = open("{0}/kind_{1}/{2}".format(DATA_DIRECTORY, otype, f), "r")
    reader = records.RecordsReader(raw)
    last = ""
    for record in reader:
        entity_proto = entity_pb.EntityProto(contents=record)
        entity = datastore.Entity.FromPb(entity_proto)
        key = entity_proto.key()
        elems = key.path()
        the_type = elems.element_list()[-1].type()
        if the_type in objects:
            write_object(outs, the_type, entity)
            count[otype] += 1


def get_files(otype):
    allfiles = os.listdir("{0}/kind_{1}".format(DATA_DIRECTORY, otype))
    allfiles = [f for f in allfiles if f.startswith("output-")]
    return allfiles
    # return ['output-205']


def main():
    outs = set_up_outputs()
    for o in objects:
        if not o in count:
            count[o] = 0
        print("processing {}".format(o))
        files = get_files(o)
        print("found {} files".format(len(files)))
        for f in progressbar.progressbar(files):
            readfile(f, o, outs)
        print("found {}".format(count[o]))
    close_outputs(outs)


if __name__ == "__main__":
    main()
