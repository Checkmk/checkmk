#This config file adds the name of each nagvis map contaning a host as custom macro.
#The information is used for the nagvis_icon.py to show a nagvis icon in the gui

# Just place this file to check_mk/conf.d

_path = '/omd/sites/%s/etc/nagvis/maps/*.cfg' % omd_site
_hosts = {}
for _nm in glob.glob(_path):
    _mapname = _nm.split("/")[-1].split('.')[0]
    for _nhost in [ _l for _l in file(_nm).readlines() if _l.startswith('host_name')]:
        _nhost =  _nhost.split('=')[-1].strip() 
        _hosts.setdefault(_nhost, [])
        _hosts[_nhost].append(_mapname)

extra_host_conf['_nagvismaps'] = []
for _nhost, _maps in _hosts.items():
    extra_host_conf['_nagvismaps'].append( ( ",".join(_maps), [_nhost] ) ) 

