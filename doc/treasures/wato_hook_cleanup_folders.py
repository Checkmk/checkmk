#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.paths
from cmk.utils.site import omd_site


# put this script into local/share/check_mk/web/plugins/wato
# of a slave site
# this deletes all WATO folders immediatelly after sync except one
# folder with the same name as the site name of the slave site
#
# it can be used to avoid a customer to see config of other customers
# for this to work you need to have one folder per customer on the top
# level and one site per customer with exactly the same name
def pre_activate_changes_cleanup(_unused):
    log = open('%s/tmp/hook.log' % cmk.utils.paths.omd_root, 'w')
    log.write('omd_site: %s, omd_root: %s\n' % (omd_site(), cmk.utils.paths.omd_root))
    confd = "%s/etc/check_mk/conf.d/wato/" % cmk.utils.paths.omd_root
    for _dirname, dirnames, _filenames in os.walk(confd):
        for subdirname in dirnames:
            if subdirname == cmk.utils.paths.omd_site:
                log.write("keeping subdir: %s\n" % subdirname)
            else:
                log.write("deletinging subdir: %s\n" % subdirname)
                shutil.rmtree(confd + subdirname)
        break
    log.close()


register_hook('pre-activate-changes', pre_activate_changes_cleanup)
