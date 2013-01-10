#!/usr/bin/python
#Author Bastian Kuhn <bk@mathias-kettner.de>

#This file is a Multisite Snapin which will show
#a the dokuwiki navigation menu if set
#Place the file to ~/local/share/check/web/plugins/sidebar
#and restart apacher.

def render_wiki():
    import re
    filename = defaults.omd_root + '/var/dokuwiki/data/pages/sidebar.txt'
    start_ul = True
    ul_started = False
    try:
        for line in file(filename).readlines():
            line = line.strip()
            if line == "":
                if ul_started == True:
                    html.write("</ul>")
                    start_ul = True
                    ul_started = False
                html.write("<br />")
            elif line == "----":
                html.write("<hr>")

            elif line.startswith("*"):
                if start_ul == True:
                    html.write("<ul>")
                    start_ul = False
                    ul_started = True

                erg = re.findall('\[\[(.*)\]\]', line)
                if len(erg) == 0:
                    continue
                erg = erg[0].split('|')
                if len(erg) > 1:
                    link = erg[0]
                    name = erg[1]
                else:
                    link = erg[0]
                    name = erg[0]


                if link.startswith("http://") or link.startswith("https://"):
                    html.write('<li>')
                    simplelink(name, link, "_blank")
                    html.write('</li>')
                else:
                    erg = name.split(':')
                    if len(erg) > 0:
                        name = erg[-1]
                    else:
                        name = erg[0]
                    bulletlink(name, "/%s/wiki/doku.php?id=%s" % (defaults.omd_site, link))

            else:
                html.write(line)

        if ul_started == True:
            html.write("</ul>")
    except IOError:
        html.write("You have to create a sidebar first")
        
    html.write("<hr>")
    html.javascript("""
    function wiki_search()
    {
        var oInput = document.getElementById('wikisearch_input');
        top.frames["main"].location.href = 
           "/%s/wiki/doku.php?do=search&id=" + escape(oInput.value);
    }
    """ % defaults.omd_site)
    html.begin_form("wikisearch", onsubmit="wiki_search();")
    html.text_input("search", "", id="wikisearch_input", )
    html.end_form()


sidebar_snapins["wiki"] = {
    "title" : _("Wiki"),
    "description" : _("Shows the Wiki Navigation of the OMD Site"),
    "render" : render_wiki,
    "allowed" : [ "admin", "user", "guest" ],
    "styles" : """
    input#wikisearch_input {
        margin-top: 3px;
        width: 222px;
    }
    """


}

