# -*- encoding: utf-8; py-indent-offset: 4 -*-
def paint_wiki_notes(row):
    host = row["host_name"]
    svc = row.get("service_description")
    svc = svc.replace(':','')
    svc = svc.replace('/','')
    svc = svc.replace('\\','')
    svc = svc.lower()
    host = host.lower()
    filename = defaults.omd_root + '/var/dokuwiki/data/pages/docu/%s/%s.txt' % (host, svc)
    if not os.path.isfile(filename):
        filename = defaults.omd_root + '/var/dokuwiki/data/pages/docu/default/%s.txt' % (svc,)
   
    text = u"<a href='../wiki/doku.php?id=docu:default:%s'>Edit Default Instructions</a> - " %  svc
    text += u"<a href='../wiki/doku.php?id=docu:%s:%s'>Edit Host Instructions</a> <hr> " % (host, svc)

    try:
        import codecs
        text += codecs.open(filename, "r", "utf-8").read()
    except IOError:
        text += "No instructions found in " + filename
    
    return "", text + "<br /><br />"

multisite_painters["svc_wiki_notes"] = {
    "title"   : _("Instructions"),
    "short"   : _("Instr"),
    "columns" : [ "host_name", "service_description" ],
    "paint"   : paint_wiki_notes,
}
