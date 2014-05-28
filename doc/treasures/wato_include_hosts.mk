
# This file needs to be appended to the existing hosts.mk file
# Upon parsing the hosts.mk file the include dir is evaluated.
# Within the include dir there are host definition files with the format
#
# ipaddress:1.2.3.4
# tag_agent:cmk-agent
# tag_criticality:critical
# tag_networking:lan
# alias:Alias of Host A
#
# If the WATO folder is saved the already existing hosts are merged with
# the hosts of the included files. After the hosts.mk is newly written this
# script appendix is removed, too.

_include_dir = ".devops"

import os, inspect
def add_host_data(_filename):
    global all_hosts, host_attributes, ipaddresses, extra_host_conf

    try:
        _host_ip         = None
        _tags_plain      = []
        _host_attributes = {}
        _alias           = None

        _lines = file(_filename).readlines()
        _hostname = os.path.basename(_filename)
        for _line in _lines:
            _what, _data = _line.split(":",1)
            _data = _data[:-1]
            if _what.startswith("tag_"):
                _tags_plain.append(_data)
            elif _what == "ipaddress":
                _host_ip = _data
            elif _what == "alias":
                _alias   = _data
            _host_attributes.update({_what: _data})


        all_hosts += [ _hostname + "|" + "|".join(_tags_plain) + "|/" + FOLDER_PATH + "/" ]
        if _host_ip:
            ipaddresses.update({_hostname: _host_ip})

        if _alias:
            extra_host_conf.setdefault('alias', []).extend([(_alias, [_hostname])])

        host_attributes.update({_hostname: _host_attributes})
    except Exception, e:
        pass

_hosts_mk_path = os.path.dirname(inspect.getsourcefile(lambda _: None))
for _dirpath, _dirname, _filenames in os.walk(_hosts_mk_path + "/" + _include_dir):
    for _filename in _filenames:
        if _filename.startswith("."):
            continue
        # Host ist bereits im Montoring -> nichts weiter tun
        for _hh in all_hosts:
            if _hh.startswith(_filename + "|"):
                continue

        # Host ins monitoring aufnehmen
        add_host_data("%s/%s" % (_dirpath, _filename))


# TODO: remove hosts where no include file pendant is available
# This can be done by evaluating the host tag for the wato folder
