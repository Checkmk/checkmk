#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Self

import pytest

from tests.testlib.extensions import (
    compatible_extensions_sorted_by_n_downloads,
    download_extension,
    install_extensions,
)
from tests.testlib.site import Site

from cmk.ccc.version import __version__, parse_check_mk_version

NUMBER_OF_EXTENSIONS_TO_COVER = 120


CURRENTLY_UNDER_TEST = {
    "https://exchange.checkmk.com/api/packages/download/101/dovereplstat-4.3.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/103/dynamicscrm-0.4.mkp",
    "https://exchange.checkmk.com/api/packages/download/104/ecallch-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/112/entropy_avail-5.2.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/112/entropy_avail-5.2.4.mkp",
    "https://exchange.checkmk.com/api/packages/download/128/filehandles-3.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/12/apcaccess-5.2.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/133/freebox-v6-2.3.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/134/gamatronic-1.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/142/huawei-2.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/145/icpraid-5.2.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/146/imap-3.0.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/14/apt-3.4.4.mkp",
    "https://exchange.checkmk.com/api/packages/download/153/jenkins-0.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/159/kemplb-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/161/kentix_devices-3.0.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/163/last_windows_update-1.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/170/lsbrelease-5.7.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/171/lvm-2.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/176/mailman_queues-5.2.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/181/memcached-5.7.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/184/mikrotik-2.4.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/184/mikrotik-2.5.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/187/mongodb-1.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/18/aspsms-1.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/197/mysql_performance-1.0.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/19/aufs-4.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/200/mysql_status-4.0.4.mkp",
    "https://exchange.checkmk.com/api/packages/download/209/netifaces-7.0.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/209/netifaces-7.1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/21/backupexec_job-1.6.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/225/perfcalc-6.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/234/querx_webtherm-1.2.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/236/Radius-0.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/238/raritan_pdu_outlets-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/242/ricoh_used-1.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/244/rspamd-1.4.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/245/sap_hana-1.9.8.mkp",
    "https://exchange.checkmk.com/api/packages/download/257/sonicwall-1.4.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/261/sslcertificates-8.8.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/263/ssllabs-3.1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/267/sync_check_multi-1.3.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/268/synology-nas-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/269/systemd-0.6.mkp",
    "https://exchange.checkmk.com/api/packages/download/275/uname-2.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/279/veeamagent-1.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/281/VMware_VCSA_Services_HealthStatus_API_Monitoring-1.0.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/284/webinject-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/291/windows_os_info-2.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/2/act-mkeventd-1.4.0p31.mkp",
    "https://exchange.checkmk.com/api/packages/download/307/amavis-6.1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/309/ceph-11.17.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/316/fail2ban-1.3.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/318/fortigate_ipsec_p1-1.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/319/hpsa-8.4.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/320/postgres_replication-1.2.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/321/SIGNL4-2.1.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/324/huawei_wlc-1.0.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/325/net_backup-1.0.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/330/export_view-1.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/332/win_scheduled_task-2.4.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/333/winnfs-1.1.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/334/php_fpm-0.20.mkp",
    "https://exchange.checkmk.com/api/packages/download/335/a10_loadbalancer-1.0.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/336/puppet_agent-1.0.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/337/qemu-2.0.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/339/EnterpriseAlert-1.5.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/341/qnap-1.4.5.mkp",
    "https://exchange.checkmk.com/api/packages/download/342/ups_alarms-1.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/346/smseagle-2.0.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/358/proxmox_qemu_backup-1.3.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/361/win_adsync-2.2.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/362/yum-2.4.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/362/yum-2.4.4.mkp",
    "https://exchange.checkmk.com/api/packages/download/365/cisco_sb_fans-2.0.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/369/veeam_o365-2.6.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/36/check_mk_api-5.5.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/370/wireguard-1.5.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/371/esendex-2.4.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/375/robotmk.v1.4.1-cmk2.mkp",
    "https://exchange.checkmk.com/api/packages/download/378/emcunity-2.2.4.mkp",
    "https://exchange.checkmk.com/api/packages/download/379/proxmox_provisioned-1.3.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/390/msexch_database_size-1.2.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/391/webchecks-57.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/3/adsl_line-1.4.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/400/veeamcc_tenant-0.4c.mkp",
    "https://exchange.checkmk.com/api/packages/download/403/access_logs-1.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/404/telegram_notifications-2.0.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/405/jb_fls-1.0.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/406/snia_sml-2.0.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/411/mirth-1.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/416/data2label-2.3.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/418/acgateway-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/420/rki_covid-1.1.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/421/dell_storage-0.6.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/422/mk_filehandler_bakery-0.3.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/423/jenkinsjobs-1.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/425/cisco_bgp_peer.mkp",
    "https://exchange.checkmk.com/api/packages/download/426/MSTeams-2.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/427/vsan-2.2.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/443/language-pack_japanese-1.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/444/language-pack_spanish-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/447/language-pack_french-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/448/language-pack_dutch-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/449/telegram_notify.mkp",
    "https://exchange.checkmk.com/api/packages/download/452/urbackup_check-2.0.5.mkp",
    "https://exchange.checkmk.com/api/packages/download/467/check_snmp-0.5.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/468/check_snmp_metric-0.4.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/469/bgp_peer.mkp",
    "https://exchange.checkmk.com/api/packages/download/46/cisco_bgp_peer-20180525.v.0.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/474/hello_world-0.1.3.mkp",
    "https://exchange.checkmk.com/api/packages/download/478/fail2ban-1.9.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/483/ABAS_Licenses-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/489/telegram_bulk-1.0.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/490/nvidia-gpu-2.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/49/cisco_inv_cdp-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/503/cve_2021_44228_log4j_cmk20.mkp",
    "https://exchange.checkmk.com/api/packages/download/506/spit_defender_state-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/509/lenovo_xclarity-2.7.mkp",
    "https://exchange.checkmk.com/api/packages/download/50/cisco_inv_lldp-1.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/510/hpe_ilo-4.0.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/512/unifi-2.2.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/518/pihole_special_agent-1.0.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/519/unifi_controller-0.83.mkp",
    "https://exchange.checkmk.com/api/packages/download/520/netapp_eseries-3.0.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/534/dell_idrac_redfish-1.8.mkp",
    "https://exchange.checkmk.com/api/packages/download/535/vcsa7_health_status-3.0.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/536/fileconnector-3.4.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/544/msteams-1.2.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/544/msteams-1.2.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/559/nextcloud-1.2.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/560/dell_os10_chassis-1.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/571/openvpn_clients-0.4.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/590/pure-1.4.7.mkp",
    "https://exchange.checkmk.com/api/packages/download/595/arista-1.0.4.mkp",
    "https://exchange.checkmk.com/api/packages/download/5/agent_ntnx-4.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/604/nut-2.0.4.mkp",
    "https://exchange.checkmk.com/api/packages/download/609/btrfs_health-1.0.16.mkp",
    "https://exchange.checkmk.com/api/packages/download/622/Nextcloud-2.5.2.mkp",
    "https://exchange.checkmk.com/api/packages/download/628/powerscale-2.1.4.mkp",
    "https://exchange.checkmk.com/api/packages/download/650/telematik_konnektor-1.3.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/652/redfish-2.2.19.mkp",
    "https://exchange.checkmk.com/api/packages/download/652/redfish-2.2.30.mkp",
    "https://exchange.checkmk.com/api/packages/download/652/redfish-2.2.31.mkp",
    "https://exchange.checkmk.com/api/packages/download/653/m365_service_health-1.2.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/669/mshpc_jobs_and_nodes-1.0.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/681/Mailcow-1.2.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/683/nutanix_prism-5.0.7.mkp",
    "https://exchange.checkmk.com/api/packages/download/77/cpufreq-2.3.1.mkp",
    "https://exchange.checkmk.com/api/packages/download/89/dell_omsa-3.0.mkp",
    "https://exchange.checkmk.com/api/packages/download/91/dell_sc-3.2.mkp",
}

UNTESTABLE = {
    # This one can't be installed anymore. It tries to deploy a part called 'pnp-rraconf'
    "https://exchange.checkmk.com/api/packages/download/97/dir_size-1.1.1.mkp",
}


@dataclasses.dataclass(frozen=True, kw_only=True)
class ImportErrors:
    base_errors: set[str] = dataclasses.field(default_factory=set)
    gui_errors: set[str] = dataclasses.field(default_factory=set)

    @classmethod
    def collect_from_site(cls, site: Site) -> Self:
        return cls(
            base_errors=set(
                json.loads(site.python_helper("_helper_failed_base_plugins.py").check_output())
            ),
            gui_errors=set(
                json.loads(site.python_helper("_helper_failed_gui_plugins.py").check_output())
            ),
        )


_DOWNLOAD_URL_BASE = "https://exchange.checkmk.com/api/packages/download/"


_EXPECTED_IMPORT_ERRORS: Mapping[str, ImportErrors] = {
    "MSTeams-2.1.mkp": ImportErrors(
        gui_errors={
            "wato/msteams: name 'socket' is not defined",
        }
    ),
    "cve_2021_44228_log4j_cmk20.mkp": ImportErrors(
        gui_errors={
            "views/inv_cve_2021_22448_log4j: No module named 'cmk.gui.plugins.views.inventory'",
        },
    ),
    "veeam_o365-2.6.1.mkp": ImportErrors(
        gui_errors={
            "metrics/veeam_o365jobs: cannot import name 'check_metrics' from 'cmk.gui.plugins.metrics.utils' (/omd/sites/ext_comp_1/lib/python3/cmk/gui/plugins/metrics/utils.py)",
            "metrics/veeam_o365licenses: cannot import name 'check_metrics' from 'cmk.gui.plugins.metrics.utils' (/omd/sites/ext_comp_1/lib/python3/cmk/gui/plugins/metrics/utils.py)",
        },
    ),
    "kentix_devices-3.0.1.mkp": ImportErrors(
        base_errors={
            "Error in agent based plugin kentix_devices: No module named "
            "'cmk.base.plugins.agent_based.utils.humidity'\n",
        }
    ),
    "pure-1.4.7.mkp": ImportErrors(
        base_errors={
            "Error in agent based plugin pure_arraydetails: cannot import name "
            "'get_percent_human_readable' from 'cmk.agent_based.legacy.v0_unstable' "
            "(/omd/sites/ext_comp_1/lib/python3/cmk/agent_based.legacy.v0_unstable.py)\n",
        }
    ),
    "fail2ban-1.3.1.mkp": ImportErrors(gui_errors={"wato/fail2ban: name 'Tuple' is not defined"}),
    "perfcalc-6.0.mkp": ImportErrors(
        gui_errors={
            "wato/perfcalc: cannot import name 'HostTagCondition' from "
            "'cmk.gui.plugins.wato' (unknown location)",
        }
    ),
    "fileconnector-3.4.0.mkp": ImportErrors(
        gui_errors={
            "wato/fileconnector: cannot import name 'FullPathFolderChoice' from "
            "'cmk.gui.plugins.wato' (unknown location)",
        }
    ),
    "gamatronic-1.0.mkp": ImportErrors(
        base_errors={
            "Error in agent based plugin gamatronic_bat_status: No module named "
            "'cmk.base.plugins.agent_based.utils.ups'\n",
        }
    ),
    "ssllabs-3.1.1.mkp": ImportErrors(
        gui_errors={"wato/ssllabs_datasource_programs: name 'Integer' is not defined"}
    ),
    "qnap-1.4.5.mkp": ImportErrors(
        gui_errors={
            "wato/check_parameters_qnap_fans: name 'Tuple' is not defined",
            "wato/check_parameters_qnap_temp: name 'Tuple' is not defined",
        }
    ),
    "imap-3.0.0.mkp": ImportErrors(
        gui_errors={
            "wato/active_checks_imap: cannot import name 'RulespecGroupActiveChecks' from "
            "'cmk.gui.plugins.wato.active_checks.common' "
            "(/omd/sites/ext_comp_1/lib/python3/cmk/gui/plugins/wato/active_checks/common.py)",
        }
    ),
    "postgres_replication-1.2.1.mkp": ImportErrors(
        gui_errors={"wato/postgres_replication: name 'DropdownChoice' is not defined"}
    ),
    "ups_alarms-1.2.mkp": ImportErrors(
        base_errors={
            "Error in agent based plugin ups_alarms: No module named "
            "'cmk.base.plugins.agent_based.utils.ups'\n",
        }
    ),
    "mirth-1.3.mkp": ImportErrors(
        gui_errors={"wato/check_parameters_mirth_stats: name 'Tuple' is not defined"}
    ),
    "veeamcc_tenant-0.4c.mkp": ImportErrors(
        gui_errors={"wato/veeamcc_tenant: name 'Tuple' is not defined"}
    ),
    "access_logs-1.2.mkp": ImportErrors(
        gui_errors={"wato/access_logs: name 'Tuple' is not defined"}
    ),
    "emcunity-2.2.4.mkp": ImportErrors(
        gui_errors={
            "metrics/emcunity: No module named 'cmk.gui.plugins.metrics.check_mk'",
            "wato/emcunity_datasource_programs: name 'Tuple' is not defined",
        }
    ),
    "systemd-0.6.mkp": ImportErrors(
        gui_errors={"wato/systemd: name 'DropdownChoice' is not defined"}
    ),
    "webinject-1.1.mkp": ImportErrors(
        gui_errors={"wato/active_checks_webinject: name 'Tuple' is not defined"}
    ),
    "adsl_line-1.4.0.mkp": ImportErrors(
        base_errors={
            "Error in agent based plugin adsl_line: cannot import name "
            "'_cleanup_if_strings' from 'cmk.base.plugins.agent_based.utils.interfaces' "
            "(/omd/sites/ext_comp_1/lib/python3/cmk/base/plugins/agent_based/utils/interfaces.py)\n",
        }
    ),
    "huawei-2.3.mkp": ImportErrors(
        gui_errors={"metrics/huawei: name 'df_translation' is not defined"}
    ),
    "proxmox_qemu_backup-1.3.0.mkp": ImportErrors(
        gui_errors={
            "wato/check_parameters_proxmox_qemu_backup: name 'DropdownChoice' is not defined",
        }
    ),
    "unifi-2.2.1.mkp": ImportErrors(
        base_errors={
            "Error in agent based plugin unifi: cannot import name 'TableRow' from "
            "'cmk.base.api.agent_based.inventory_classes' "
            "(/omd/sites/ext_comp_1/lib/python3/cmk/base/api/agent_based/inventory_classes.py)\n",
        }
    ),
    "cisco_bgp_peer-20180525.v.0.2.mkp": ImportErrors(
        gui_errors={"wato/cisco_bgp_peer: name 'Integer' is not defined"}
    ),
    "act-mkeventd-1.4.0p31.mkp": ImportErrors(
        gui_errors={
            "dashboard/acteventstat: No module named 'sites'",
            "sidebar/acteventstat: No module named 'sites'",
            "views/actmkeventd: No module named 'sites'",
            "visuals/actmkeventd: No module named 'mkeventd'",
            "wato/actmkeventd: No module named 'sites'",
            "wato/event2live: No module named 'cmk.defines'",
        }
    ),
    "nextcloud-1.2.2.mkp": ImportErrors(
        gui_errors={
            "wato/nextcloud_data_extension: cannot import name "
            "'RulespecGroupIntegrateOtherServices' from "
            "'cmk.gui.plugins.wato.active_checks' "
            "(/omd/sites/ext_comp_1/lib/python3/cmk/gui/plugins/wato/active_checks/__init__.py)",
        }
    ),
    "puppet_agent-1.0.1.mkp": ImportErrors(
        gui_errors={"wato/puppet_agent: name 'DropdownChoice' is not defined"}
    ),
    "net_backup-1.0.2.mkp": ImportErrors(
        gui_errors={"wato/net_backup: name 'DropdownChoice' is not defined"}
    ),
    "telegram_bulk-1.0.0.mkp": ImportErrors(
        gui_errors={"wato/telegram: name 'TextAreaUnicode' is not defined"}
    ),
    "cisco_inv_lldp-1.1.mkp": ImportErrors(
        gui_errors={"views/my_inv_lldp: name 'inventory_displayhints' is not defined"}
    ),
    "mshpc_jobs_and_nodes-1.0.0.mkp": ImportErrors(
        gui_errors={"wato/rulespec_agent_mshpc: name 'HTTPUrl' is not defined"}
    ),
    "dynamicscrm-0.4.mkp": ImportErrors(
        gui_errors={
            "metrics/dynamicscrm: name 'df_translation' is not defined",
            "wato/dynamicscrm: name 'Tuple' is not defined",
        }
    ),
    "nutanix_prism-5.0.7.mkp": ImportErrors(
        base_errors={
            "Error in agent based plugin prism_cluster_cpu: No module named "
            "'cmk.base.plugins.agent_based.utils.cpu_util'\n",
            "Error in agent based plugin prism_host_stats: No module named "
            "'cmk.base.plugins.agent_based.utils.cpu_util'\n",
            "Error in agent based plugin prism_vm_stats: No module named "
            "'cmk.base.plugins.agent_based.utils.memory'\n",
        }
    ),
    "bgp_peer.mkp": ImportErrors(
        gui_errors={"views/inv_bgp_peer: No module named 'cmk.gui.plugins.views.inventory'"}
    ),
    "backupexec_job-1.6.1.mkp": ImportErrors(
        gui_errors={"wato/backupexec_job: name 'Tuple' is not defined"}
    ),
    "agent_ntnx-4.0.mkp": ImportErrors(
        gui_errors={
            "wato/check_parameters_ntnx: name 'Tuple' is not defined",
            "wato/datasource_programs_ntnx: name 'ListChoice' is not defined",
        }
    ),
    "sync_check_multi-1.3.1.mkp": ImportErrors(
        gui_errors={
            "wato/sync_check_multi: cannot import name 'add_replication_paths' from "
            "'cmk.gui.watolib' "
            "(/omd/sites/ext_comp_1/lib/python3/cmk/gui/watolib/__init__.py)",
        }
    ),
    "sap_hana-1.9.8.mkp": ImportErrors(
        gui_errors={
            "metrics/sap_hana: name 'df_translation' is not defined",
            "wato/sap_hana: name 'CascadingDropdown' is not defined",
            "wato/sap_hana_backup: name 'Tuple' is not defined",
            "wato/sap_hana_license: name 'Tuple' is not defined",
            "wato/sap_hana_memrate: name 'CascadingDropdown' is not defined",
        }
    ),
    "uname-2.0.mkp": ImportErrors(
        gui_errors={"wato/check_parameters_uname: name 'RegExp' is not defined"}
    ),
    "last_windows_update-1.0.mkp": ImportErrors(
        gui_errors={"wato/agent_bakery_last_windows_updates: name 'DropdownChoice' is not defined"}
    ),
    "mongodb-1.0.mkp": ImportErrors(
        gui_errors={"wato/active_checks_mongodb: name 'Tuple' is not defined"}
    ),
    "Radius-0.1.mkp": ImportErrors(
        gui_errors={"wato/check_radius: name 'register_rulegroup' is not defined"}
    ),
    "dell_storage-0.6.1.mkp": ImportErrors(
        base_errors={
            "Error in agent based plugin dell_storage_disk: cannot import name 'diskstat' "
            "from 'cmk.base.plugins.agent_based.utils' (unknown location)\n",
            "Error in agent based plugin dell_storage_port: cannot import name 'diskstat' "
            "from 'cmk.base.plugins.agent_based.utils' (unknown location)\n",
            "Error in agent based plugin dell_storage_volume: cannot import name "
            "'diskstat' from 'cmk.base.plugins.agent_based.utils' (unknown location)\n",
        }
    ),
    "jenkins-0.3.mkp": ImportErrors(gui_errors={"wato/jenkins: name 'ListOf' is not defined"}),
    "cisco_inv_cdp-1.1.mkp": ImportErrors(
        gui_errors={"views/my_inv_cdp: name 'inventory_displayhints' is not defined"}
    ),
    "filehandles-3.2.mkp": ImportErrors(
        gui_errors={
            "wato/filehandles: (unicode error) 'unicodeescape' codec can't decode bytes "
            "in position 51-52: malformed \\N character escape (filehandles.py, line 128)",
        }
    ),
    "lvm-2.1.mkp": ImportErrors(
        gui_errors={"wato/agent_bakery_lvm: name 'DropdownChoice' is not defined"}
    ),
    "windows_os_info-2.3.mkp": ImportErrors(
        gui_errors={"wato/agent_bakery_windows_os_info: name 'DropdownChoice' is not defined"}
    ),
    "m365_service_health-1.2.1.mkp": ImportErrors(
        base_errors={
            "Error in agent based plugin m365_service_health: cannot import name "
            "'IgnoreResults' from 'cmk.base.api.agent_based.checking_classes' "
            "(/omd/sites/ext_comp_1/lib/python3/cmk/base/api/agent_based/checking_classes.py)\n",
        }
    ),
}


def _get_tested_extensions() -> Iterable[tuple[str, str]]:
    return [(url, url.rsplit("/", 1)[-1]) for url in CURRENTLY_UNDER_TEST]


@pytest.mark.parametrize(
    "extension_download_url, name",
    [pytest.param(url, name, id=name) for url, name in _get_tested_extensions()],
)
def test_extension_compatibility(
    site: Site,
    extension_download_url: str,
    name: str,
) -> None:
    site.write_file(
        extension_filename := "tmp.mkp",
        download_extension(extension_download_url),
    )
    with install_extensions(site, [site.resolve_path(Path(extension_filename))]):
        encountered_errors = ImportErrors.collect_from_site(site)
        expected_errors = _EXPECTED_IMPORT_ERRORS.get(name, ImportErrors())

    assert encountered_errors.base_errors == expected_errors.base_errors
    assert encountered_errors.gui_errors == expected_errors.gui_errors


def test_package_list_up_to_date() -> None:
    parsed_version = parse_check_mk_version(__version__)
    extensions = compatible_extensions_sorted_by_n_downloads(parsed_version)

    # uncomment this to get output that you can paste into a spreadsheet.
    # for extension in extensions:
    #     print(f"{extension.latest_version.link}\t{extension.downloads:5}")
    # assert False

    must_haves = {e.latest_version.link for e in extensions[:NUMBER_OF_EXTENSIONS_TO_COVER]}

    missing_test_cases = must_haves - set(CURRENTLY_UNDER_TEST) - UNTESTABLE
    assert not missing_test_cases
