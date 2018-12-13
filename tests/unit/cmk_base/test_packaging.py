#!/usr/bin/env python

import cmk_base.packaging as packaging


def test_package_parts():
    assert packaging.get_package_parts() == [
        packaging.PackagePart('checks', 'Checks', 'local/share/check_mk/checks'),
        packaging.PackagePart('notifications', 'Notification scripts',
                              'local/share/check_mk/notifications'),
        packaging.PackagePart('inventory', 'Inventory plugins', 'local/share/check_mk/inventory'),
        packaging.PackagePart('checkman', "Checks' man pages", 'local/share/check_mk/checkman'),
        packaging.PackagePart('agents', 'Agents', 'local/share/check_mk/agents'),
        packaging.PackagePart('web', 'Multisite extensions', 'local/share/check_mk/web'),
        packaging.PackagePart('pnp-templates', 'PNP4Nagios templates',
                              'local/share/check_mk/pnp-templates'),
        packaging.PackagePart('doc', 'Documentation files', 'local/share/doc/check_mk'),
        packaging.PackagePart('locales', 'Localizations', 'local/share/check_mk/locale'),
        packaging.PackagePart('bin', 'Binaries', 'local/bin'),
        packaging.PackagePart('lib', 'Libraries', 'local/lib'),
        packaging.PackagePart('mibs', 'SNMP MIBs', 'local/share/snmp/mibs'),
        packaging.PackagePart('alert_handlers', 'Alert handlers',
                              'local/share/check_mk/alert_handlers'),
    ]


def test_config_parts():
    assert packaging.config_parts == [
        packaging.PackagePart("ec_rule_packs", "Event Console rule packs",
                              "etc/check_mk/mkeventd.d/mkp/rule_packs")
    ]
