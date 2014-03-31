#!/usr/bin/python
# Please refer to nagvis_icon.mk to see a way how to add the nagvismaps custom macro

# copy me to ~/local/share/check_mk/web/pluins/icon and restart the site apache

def paint_nagvis_image(what, row, tags, custom_vars):
    if what != 'host' or not custom_vars.get('NAGVISMAPS'):
        return
    h = ""
    for nagvis_map in custom_vars['NAGVISMAPS'].split(','):
        h += '<a href="../nagvis/frontend/nagvis-js/index.php?mod=Map&act=view&show=%s" title="%s"><img class=icon src="images/icon_nagvis.png"/></a>' \
        % ( nagvis_map, nagvis_map )

    return h

multisite_icons.append({
    'paint':           paint_nagvis_image,
})
