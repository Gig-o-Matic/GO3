# -*- coding: UTF-8 -*-
# read the output from an appengine backup and parse to CSV files


# Make sure App Engine APK is available
import sys, os
sys.path.append('/usr/local/google_appengine')
from google.appengine.api.files import records
from google.appengine.datastore import entity_pb
from google.appengine.api import datastore
import progressbar
import random

DEBUG=False

# order is important
objects=[
         'Band', 
         'Section', 
         'Member', 
         'Assoc', 
        #  'Gig', 
        #  'Plan', 
        #  'Comment'
        ]
count={}

columns={
    'Band': ['show_in_nav', 'hometown', 'member_links', 'new_member_message','timezone', 'anyone_can_create_gigs',
             'condensed_name', 'share_gigs', 'band_cal_feed_dirty', 'rss_feed', 'pub_cal_feed_dirty', 'shortname',
             'enable_forum', 'website', 'description', 'send_updates_by_default', 'thumbnail_img', 'anyone_can_manage_gigs',
             'simple_planning', 'plan_feedback', 'name', 'created', 'lower_name', 'images'],
    'Section': ['name'],
    'Member': ['preferences.default_view','email_address','preferences.email_new_gig','show_long_agenda','display_name',
               'pending_change_email', 'preferences.locale','is_superuser','seen_motd_time','statement','preferences.share_email',
               'is_betatester','seen_motd','updated','preferences.agenda_show_time','phone','is_band_editor','seen_welcome',
               'verified','nickname','name','created', 'preferences.calendar_show_only_committed', 'preferences.share_profile',
               'preferences.calendar_show_only_confirmed', 'preferences.hide_canceled_gigs','created'],
    'Gig': ['creator','is_archived','is_in_trash','trueenddate','dress','archive_id','trashed_date',
            'is_canceled','is_confirmed','title','details','default_to_attending', 'leader',
            'status', 'comment_id', 'hide_from_calendar', 'calltime', 'paid', 'address', 'date', 
            'invite_occasionals', 'endtime', 'is_private', 'was_reminded', 'enddate', 'rss_description',
            'setlist', 'contact', 'settime', 'created_date', 'postgig'],
    'Assoc': ['is_occasional', 'hide_from_schedule', 'is_confirmed', 'created', 'color', 'is_multisectional', 'default_section_index', 
              'default_section','is_invited', 'member','band','is_band_admin','email_me','member_name'],
    'Plan': ['comment', 'section', 'feedback_value', 'value', 'member'],
    'Comment': ['member', 'comment', 'created_date']
}

mappings = {}

DATA_DIRECTORY = 'export'
DELIMITER = '\t'

def set_up_outputs():
    outs = {}
    for o in objects:
        outs[o] = open('{}.json'.format(o), 'w')
        outs[o].write('[\n')
    return outs

def close_outputs(outs):
    for c in outs:
        outs[c].write(']')
        outs[c].close()


def make_id(entity_type, key):
    if not entity_type in mappings:
        mappings[entity_type] = {}
    id = len(mappings[entity_type])+100
    mappings[entity_type][key] = id
    return id


def key_to_str(key):
    return key.__str__()


def find_id(entity_type, key):
    val = mappings[entity_type].get(key)
    if val is None and DEBUG:
        val = 999
    return val


def get_key(entity):
    key=("\"{0}\"".format(key_to_str(entity.key()))) # key
    parent=("\"{0}\"".format(key_to_str(entity.parent()))) # parent
    return key[1:-1], parent[1:-1]

def enc(string):
    return string.encode('utf-8') if string else ''

# 'show_in_nav', 'hometown', 'member_links', 'new_member_message','timezone', 'anyone_can_create_gigs',
# 'condensed_name', 'share_gigs', 'band_cal_feed_dirty', 'rss_feed', 'pub_cal_feed_dirty', 'shortname',
# 'enable_forum', 'website', 'description', 'send_updates_by_default', 'thumbnail_img', 'anyone_can_manage_gigs',
# 'simple_planning', 'plan_feedback', 'name', 'created', 'lower_name'
def make_band_object(entity):
    key, parent = get_key(entity)

    id = make_id('Band', key)

    return """{{
    "model": "band.band",
    "pk": {0},
    "fields": {{
        "name": "{1}",
        "hometowm": "{2}",
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
    }}
}},\n""".format(id, 
                enc(entity['name']),
                enc(entity['hometown']),
                enc(entity['shortname']),
                entity['website'],
                enc(entity['description']),
                entity.get('images'),
                enc(entity['member_links']),
                entity['thumbnail_img'],
                entity['timezone'],
                enc(entity.get('new_member_message')),
                entity['anyone_can_manage_gigs'],
                entity.get('anyone_can_create_gigs',entity['anyone_can_manage_gigs']),
                entity['send_updates_by_default'],
                entity['simple_planning'],
                enc(entity['plan_feedback']),
                entity['created'].strftime('%Y-%m-%d')
        )


#    'Section': ['name'],
def make_section_object(entity):
    key, parent = get_key(entity)

    id = make_id('Section', key)
    parent_id = find_id('Band', parent)

    return """{{
        "model": "band.section",
        "pk": {0},
        "fields": {{
            "name": "{1}",
            "band": {2},
        }}
}},\n""".format(id, entity['name'].encode('utf-8'), parent_id)


# 'Member': ['preferences.default_view','email_address','preferences.email_new_gig','show_long_agenda','display_name',
#             'pending_change_email', 'preferences.locale','is_superuser','seen_motd_time','statement','preferences.share_email',
#             'is_betatester','seen_motd','updated','preferences.agenda_show_time','phone','is_band_editor','seen_welcome',
#             'verified','nickname','name','created', 'preferences.calendar_show_only_committed', 'preferences.share_profile',
#             'preferences.calendar_show_only_confirmed', 'preferences.hide_canceled_gigs','created'],
def make_member_object(entity):
    key, parent = get_key(entity)
    id = make_id('Member', key)

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
}},\n""".format(id,
                entity['email_address'],
                enc(entity['name']),
                enc(entity['nickname']),
                enc(entity['phone']),
                enc(entity['statement']),
                0, # active
                )

    pref_obj = """{{
        "model": "member.memberpreferences",
        "pk": {0},
        "fields": {{
            "member": {1},
            "hide_canceled_gigs": {2},
            "language": {3},
            "share_profile": {4},
            "share_email": {5},
            "calendar_show_only_confirmed": {6},
            "calendar_show_only_committed": {7},
            "agenda_show_time": {8},
            "default_view": {9}
    }}
}},\n""".format(id, # we'll use the same pk as the member object we're associated with
                id, # member id
                entity['preferences.hide_canceled_gigs'],
                entity['preferences.locale'],
                entity['preferences.share_profile'],
                entity['preferences.share_email'],
                entity['preferences.calendar_show_only_confirmed'],
                entity['preferences.calendar_show_only_committed'],
                entity['preferences.agenda_show_time'],
                entity['preferences.default_view'],
                )

    return "{0}\n{1}".format(member_obj, pref_obj)


# 'is_occasional', 'hide_from_schedule', 'is_confirmed', 'created', 'color', 'is_multisectional', 'default_section_index', 
#               'default_section','is_invited', 'member','band','is_band_admin','email_me','member_name'
def make_assoc_object(entity):
    key, parent = get_key(entity)
    id = make_id('Assoc', key)

    member_id = find_id('Member',key_to_str(entity['member']))
    band_id = find_id('Band',key_to_str(entity['band']))
    status = 1 if entity['is_confirmed'] else 2 if entity['is_invited'] else 0

    return """{{
        "model": "band.assoc",
        "pk": {0},
        "fields": {{
            "band": "{1}",
            "member": "{2}",
            "status": {3},
            "default_section": {4},
            "is_admin": {5},
            "is_occasional": {6},
        }}
}},\n""".format(id, 
                band_id, 
                member_id, 
                status,
                find_id('Section',key_to_str(entity['default_section'])),
                entity['is_band_admin'],
                entity['is_occasional']
                )


def make_gig_object(entity):
    key, parent = get_key(entity)
    id = make_id('Gig', key)

    parent_id = find_id('Band', parent)

    return """{{
        "model": "gig.gig",
        "pk": {0},
        "fields": {{
            "band": "{1}", 
            "title": "{2}",
        }}
}},\n""".format(id, parent_id, entity['title'].encode('utf-8'),)


def make_plan_object(entity):
    key, parent = get_key(entity)
    id = make_id('Plan', key)

    parent_id = find_id('Gig', parent)
    member_id = find_id('Member', key_to_str(entity['member']))

    if member_id is None:
        # member deleted at some point but the plan wasn't - weird
        return None

    return """{{
        "model": "gig.plan",
        "pk": {0},
        "fields": {{
            "gig": "{1}", 
            "member": "{2}",
        }}   
}},\n""".format(id, parent_id, member_id,)


def make_comment_object(entity):
    key, parent = get_key(entity)
    id = make_id('Comment', key)

    parent_id = find_id('Gig', parent)
    member_id = find_id('Member', key_to_str(entity['member']))

    if member_id is None:
        # member deleted at some point but the plan wasn't - weird
        return None

    return """{{
        "model": "gig.gigcomment",
        "pk": {0},
        "fields": {{
            "gig": "{1}", 
            "member": "{2}",
            "text": "{3}"
        }}   
}},\n""".format(id, parent_id, member_id, entity['comment'].encode('utf-8'),)


def write_object(outs, the_type, entity):

    obj = {
        'Band':make_band_object,
        'Section':make_section_object,
        'Member':make_member_object,
        'Assoc':make_assoc_object,
        'Gig':make_gig_object,
        'Plan':make_plan_object,
        'Comment':make_comment_object,
    }[the_type](entity)
    f = outs[the_type]
    if (obj):
        f.write(obj)
        f.write("\n")


def readfile(f,otype,outs):
    raw = open('{0}/{1}/{2}'.format(DATA_DIRECTORY,otype,f), 'r')
    reader = records.RecordsReader(raw)
    last = ''
    for record in reader:
        entity_proto = entity_pb.EntityProto(contents=record)
        entity = datastore.Entity.FromPb(entity_proto)
        key=entity_proto.key()
        elems = key.path()
        the_type = elems.element_list()[-1].type()
        if the_type in objects:
            write_object(outs, the_type, entity)
            count[otype] += 1

def get_files(otype):
    allfiles = os.listdir("{0}/{1}".format(DATA_DIRECTORY,otype))
    allfiles = [f for f in allfiles if f.startswith('output-')]
    return allfiles
    # return ['output-205']

def main():
    outs = set_up_outputs()
    for o in objects:
        if not o in count:
            count[o] = 0
        print('processing {}'.format(o))
        files = get_files(o)
        print('found {} files'.format(len(files)))
        for f in progressbar.progressbar(files):
            readfile(f, o, outs)
        print('found {}'.format(count[o]))
    close_outputs(outs)
    
if __name__ == '__main__':
    main()