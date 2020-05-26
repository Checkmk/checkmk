#!/usr/bin/env python
# -*- coding: utf-8 -*-
# License: GNU General Public License v2
#
# Author : thl-cmk[at]outlook[dot]com
# Date   : 2020-04-27
# Content: wato plugin for snmp check 'cisco_asa_vpnsessions'
#          to configure waring/critical levels
#

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _parameter_valuespec_cisco_asa_vpnsessions():
    return Dictionary(elements=[
        ('WarnCrit',
         Tuple(
             title=_('Number of active sessions'),
             help=_('This check monitors the number of active/peak sessions'),
             elements=[
                 Integer(title=_('Warning at'), unit=_('sessions'), default_value=10),
                 Integer(title=_('Critical at'), unit=_('sessions'), default_value=100),
             ],
         )),
    ],)


def _item_spec_cisco_asa_vpnsessions():
    return TextAscii(
        title=_('VPN session type'),
        help=_(
            'VPN session type is one of AnyConnect, Clientless, IPSec L2L, IPSec RA or Summary. '),
        allow_empty=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name='cisco_asa_vpnsessions',
        group=RulespecGroupCheckParametersNetworking,
        item_spec=_item_spec_cisco_asa_vpnsessions,
        match_type='dict',
        parameter_valuespec=_parameter_valuespec_cisco_asa_vpnsessions,
        title=lambda: _('Cisco ASA VPN sessions'),
    ))
