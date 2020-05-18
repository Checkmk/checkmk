#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
# Cisco ASA cras Sessions (SVC and L2L) metrics plugin
#
# Author: Th.L.
# Date  : 2018-02-16
#
#
#####################################################################################################################
#
# define units
#
#####################################################################################################################



#####################################################################################################################
#
# define metrics
#
#####################################################################################################################

metric_info['cisco_asa_vpnsessions_ipsecl2l_current'] = {
    'title': _('IPSec L2L sessions active'),
    'help': _('number of current active IPSec L2L sessions'),
    'unit': 'count',
    'color': '26/a',
}
metric_info['cisco_asa_vpnsessions_ipsecl2l_peak'] = {
    'title': _('IPSec L2L sessions peak'),
    'help': _('number of peak IPSec L2L sessions'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['cisco_asa_vpnsessions_anyconnect_current'] = {
    'title': _('AnyConnect sessions active'),
    'help': _('number of current active AnyConnect (SVC) sessions'),
    'unit': 'count',
    'color': '26/a',
}
metric_info['cisco_asa_vpnsessions_anyconnect_peak'] = {
    'title': _('AnyConnect sessions peak'),
    'help': _('number of peak active AnyConnect (SVC) sessions'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['cisco_asa_vpnsessions_clientless_current'] = {
    'title': _('Clientless VPN sessions active'),
    'help': _('number of current active client less (WEB) VPN sessions'),
    'unit': 'count',
    'color': '26/a',
}


metric_info['cisco_asa_vpnsessions_ipsecra_current'] = {
    'title': _('IPSec RAS sessions active'),
    'help': _('number of current active IPSec remote access sessions'),
    'unit': 'count',
    'color': '26/a',
}
metric_info['cisco_asa_vpnsessions_ipsecra_peak'] = {
    'title': _('IPSec RAS sessions peak'),
    'help': _('number of peak IPSec remote access sessions'),
    'unit': 'count',
    'color': '21/a',
}

######################################################################################################################
#
# map perfdata to metric
#
######################################################################################################################

check_metrics['check_mk-cisco_asa_vpnsessions'] = {
    'ipsecl2l_current': {'name': 'cisco_asa_vpnsessions_ipsecl2l_current', },
    'ipsecl2l_peak': {'name': 'cisco_asa_vpnsessions_ipsecl2l_peak', },
    'anyconnect_current': {'name': 'cisco_asa_vpnsessions_anyconnect_current', },
    'anyconnect_peak': {'name': 'cisco_asa_vpnsessions_anyconnect_peak', },
    'ipsecra_current': {'name': 'cisco_asa_vpnsessions_ipsecra_current', },
    'ipsecra_peak': {'name': 'cisco_asa_vpnsessions_ipsecra_peak', },
    'clientless_current': {'name': 'cisco_asa_vpnsessions_clientless_current', },
    'clientless_peak': {'name': 'cisco_asa_vpnsessions_clientless_peak', },
}

######################################################################################################################
#
# how to graph perdata
#
######################################################################################################################

graph_info.append({
    'title': _('Lan2Lan VPN Sessions'),
    'metrics': [
        ('cisco_asa_vpnsessions_ipsecl2l_current', 'area'),
        ('cisco_asa_vpnsessions_ipsecl2l_peak', 'line'),

    ],
    'range': (0, 'cisco_asa_vpnsessions_ipsecl2l_peak:max'),
    'scalars': [
        ('cisco_asa_vpnsessions_ipsecl2l_current:crit', _('crit level')),
        ('cisco_asa_vpnsessions_ipsecl2l_current:warn', _('warn level')),
    ],
})
graph_info.append({
    'title': _('Anyconnect VPN Sessions'),
    'metrics': [
        ('cisco_asa_vpnsessions_anyconnect_current', 'area'),
        ('cisco_asa_vpnsessions_anyconnect_peak', 'line'),

    ],
    'range': (0, 'cisco_asa_vpnsessions_anyconnect_peak:max'),
    'scalars': [
        ('cisco_asa_vpnsessions_anyconnect_current:crit', _('crit level')),
        ('cisco_asa_vpnsessions_anyconnect_current:warn', _('warn level')),
    ],
})
graph_info.append({
    'title': _('IPSec RAS VPN Sessions'),
    'metrics': [
        ('cisco_asa_vpnsessions_ipsecra_current', 'area'),
        ('cisco_asa_vpnsessions_ipsecra_peak', 'line'),

    ],
    'range': (0, 'cisco_asa_vpnsessions_ipsecra_peak:max'),
    'scalars': [
        ('cisco_asa_vpnsessions_ipsecra_current:crit', _('crit level')),
        ('cisco_asa_vpnsessions_ipsecra_current:warn', _('warn level')),
    ],
})
graph_info.append({
    'title': _('Clientless (WEB) VPN Sessions'),
    'metrics': [
        ('cisco_asa_vpnsessions_clientless_current', 'area'),
        ('cisco_asa_vpnsessions_clientless_peak', 'line'),

    ],
    'range': (0, 'cisco_asa_vpnsessions_clientless_peak:max'),
    'scalars': [
        ('cisco_asa_vpnsessions_clientless_current:crit', _('crit level')),
        ('cisco_asa_vpnsessions_clientless_current:warn', _('warn level')),
    ],
})

######################################################################################################################
#
# define perf-o-meter
#
######################################################################################################################

cras_half_value = 500

perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'cisco_asa_vpnsessions_ipsecl2l_current',
    'half_value': cras_half_value,
    'exponent': 2,
})
perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'cisco_asa_vpnsessions_anyconnect_current',
    'half_value': cras_half_value,
    'exponent': 2,
})
perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'cisco_asa_vpnsessions_clientless_current',
    'half_value': cras_half_value,
    'exponent': 2,
})
perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'cisco_asa_vpnsessions_ipsecra_current',
    'half_value': cras_half_value,
    'exponent': 2,
})
