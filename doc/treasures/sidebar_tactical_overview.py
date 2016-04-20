#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-

# Put this into local/share/check_mk/web/plugins/sidebar. And you will get
# additional versions of "Tactical Overview" for hosts having a certain
# tag.

def create_tactical_overview_snapin(title, tag_group, tag_name):
    def create_render_function(tag_group, tag_name):
        return lambda: render_tactical_overview(
            extra_filter_headers = "Filter: host_custom_variables ~ TAGS (^|[ ])%s($|[ ])\n" % tag_name,
            extra_url_variables = [
              ( "host_tag_0_grp", tag_group ),
              ( "host_tag_0_op", "is" ),
              ( "host_tag_0_val", tag_name ),
            ])

    sidebar_snapins["tactical_overview_" + tag_name] = {
        "title" : title,
        "description" : _("Tactical overview of all hosts with the tag %s") % tag_name,
        "refresh" : True,
        "render" : create_render_function(tag_group, tag_name),
        "allowed" : [ "user", "admin", "guest" ],
        "styles" : snapin_tactical_overview_styles,
    }

# Here you declare which copies of the snapin you wnat:
create_tactical_overview_snapin(u"München", "stadt", "muc")
create_tactical_overview_snapin(u"Göttingen", "stadt", "got")
