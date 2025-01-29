#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Hashable, Mapping

from cmk.utils.sectionname import SectionName

from cmk.base.api.agent_based.plugin_classes import SectionPlugin
from cmk.base.api.agent_based.register import AgentBasedPlugins, filter_relevant_raw_sections


def test_detect_spec_dedup(
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    """Test which snmp sections share a detect spec, but do not share the code for it

    This means that they currently are detecting the same devices, but they might get out
    of sync.

    If this test turns red, the set of plug-ins that share the same detection spec has changed.
    This means that
     a) You have deduplicated code, such that plug-ins now share the same (not only "equal"!)
        detection spec. That is good, remove them from the list below!
     b) You accidently changed a detect specification where you should have changed all of them,
        or you can share a spec with another plugin. -> please turn this situation into a)!
    """
    plugins_by_detect_spec: dict[Hashable, dict[int, list[str]]] = {}
    for snmp_section in agent_based_plugins.snmp_sections.values():
        plugins_by_detect_spec.setdefault(
            tuple(tuple(e) for e in snmp_section.detect_spec), {}
        ).setdefault(id(snmp_section.detect_spec), []).append(str(snmp_section.name))

    offenders: set[tuple[str, ...]] = {
        tuple(sorted([s for sections in values.values() for s in sections]))
        for values in plugins_by_detect_spec.values()
        if len(values) > 1
    }
    assert offenders == {
        ("alcatel_timetra_chassis", "alcatel_timetra_cpu"),
        ("apc_netbotz_fluid", "apc_netbotz_smoke"),
        ("apc_netbotz_v2_other_sensors", "apc_netbotz_v2_sensors"),
        ("apc_netbotz_50_other_sensors", "apc_netbotz_50_sensors"),
        ("apc_sts_inputs", "apc_sts_source"),
        ("artec_documents", "artec_temp"),
        ("bdt_tape_info", "bdt_tape_status"),
        ("bintec_brrp_status", "bintec_sensors"),
        ("bluecoat_diskcpu", "bluecoat_sensors"),
        ("bluenet_meter", "bluenet_sensor"),
        ("cisco_asa_conn", "cisco_asa_connections"),
        ("dell_powerconnect_fans", "dell_powerconnect_psu"),
        ("docsis_channels_downstream", "docsis_channels_upstream"),
        ("emerson_stat", "emerson_temp"),
        ("fjdarye_pcie_flash_modules", "fjdarye_pools_150"),
        ("gude_humidity", "gude_temp"),
        ("h3c_lanswitch_cpu", "h3c_lanswitch_sensors"),
        ("hp_fan", "hp_psu"),
        ("hp_hh3c_fan", "hp_hh3c_power"),
        ("hp_mcs_sensors", "hp_mcs_system"),
        ("hp_proliant_systeminfo", "hp_sts_drvbox"),
        ("huawei_wlc_aps", "huawei_wlc_devs"),
        ("hwg_humidity", "hwg_temp"),
        ("ibm_tl_changer_devices", "ibm_tl_media_access_devices"),
        ("if", "inv_if"),
        ("innovaphone_priports_l1", "innovaphone_priports_l2"),
        ("ipr400_in_voltage", "ipr400_temp"),
        ("juniper_trpz_aps", "juniper_trpz_aps_sessions"),
        ("netapp_cluster", "netapp_vfiler"),
        ("nimble_latency", "nimble_volumes"),
        ("packeteer_fan_status", "packeteer_ps_status"),
        ("poseidon_inputs", "poseidon_temp"),
        ("qlogic_sanbox", "qlogic_sanbox_fabric_element"),
        ("quantum_libsmall_door", "quantum_libsmall_status"),
        ("raritan_emx", "raritan_emx_sensors"),
        ("raritan_pdu_outletcount", "raritan_pdu_plugs"),
        ("raritan_px_outlets", "raritan_px_sensors"),
        ("safenet_hsm", "safenet_ntls"),
        ("sentry_pdu_outlets_v4", "sentry_pdu_v4"),
        ("sophos", "sophos_messages"),
        ("stormshield_cluster", "stormshield_cluster_node"),
        ("teracom_tcw241_analog", "teracom_tcw241_digital"),
        ("zebra_model", "zebra_printer_status"),
        ("adva_fsp_current", "adva_fsp_if", "adva_fsp_temp"),
        ("akcp_sensor_drycontact", "akcp_sensor_humidity", "akcp_sensor_temp"),
        ("arris_cmts_cpu", "arris_cmts_mem", "arris_cmts_temp"),
        ("aruba_aps", "aruba_clients", "aruba_cpu_util"),
        ("atto_fibrebridge_chassis", "atto_fibrebridge_fcport", "atto_fibrebridge_sas"),
        ("avaya_45xx_cpu", "avaya_45xx_fan", "avaya_45xx_temp"),
        ("bdtms_tape_info", "bdtms_tape_module", "bdtms_tape_status"),
        ("cisco_srst_call_legs", "cisco_srst_phones", "cisco_srst_state"),
        ("climaveneta_alarm", "climaveneta_fan", "climaveneta_temp"),
        ("dell_idrac_fans", "dell_idrac_power", "dell_idrac_raid"),
        ("f5_bigip_cluster_status_v11_2", "f5_bigip_vcmpfailover", "f5_bigip_vcmpguests"),
        ("hp_procurve_cpu", "hp_procurve_mem", "hp_procurve_sensors"),
        ("orion_backup", "orion_batterytest", "orion_system"),
        ("pfsense_counter", "pfsense_if", "pfsense_status"),
        ("sentry_pdu", "sentry_pdu_outlets", "sentry_pdu_systempower"),
        (  # these are the same "by chance"
            "fjdarye_channel_adapters",
            "fjdarye_channel_modules",
            "fjdarye_controller_enclosures",
            "fjdarye_controller_modules_memory",
            "fjdarye_disks",
            "fjdarye_summary_status",
            "fjdarye_system_capacitors",
        ),
    }


def test_all_sections_are_subscribed_by_some_plugin(
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    """Test that all registered sections are subscribed to by some plugin

    We have very few sections that are not subscribed to by any plugin.
    We can afford to keep track of those.
    """
    allowed_unsubscribed_sections = {
        "labels",
        "azure_labels",
        "ec2_labels",
        "elb_generic_labels",
        "elbv2_generic_labels",
    }

    all_existing_sections: Mapping[SectionName, SectionPlugin] = {
        **agent_based_plugins.agent_sections,
        **agent_based_plugins.snmp_sections,
    }

    subscribed_sections_names = set(
        filter_relevant_raw_sections(
            consumers=itertools.chain(
                agent_based_plugins.check_plugins.values(),
                agent_based_plugins.inventory_plugins.values(),
            ),
            sections=all_existing_sections.values(),
        )
    )

    unsubscribed_sections_names = {
        str(n) for n in set(all_existing_sections) - subscribed_sections_names
    }

    assert unsubscribed_sections_names == allowed_unsubscribed_sections


def test_section_detection_uses_sysdescr_or_sysobjid(
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    """Make sure the first OID is the system description or the system object ID

    Checking the system description or the system object ID first increases performance
    massively, because we can reduce the number of devices for which the subsequent OIDs
    are fetched, based on an OID information we fetch anyway.

    You should really have an exceptionally good reason to add something here.

    The known exceptions cannot easily be fixed, because introducing a too strict
    criterion is an incompatible change.
    In most of the cases I was unable to spot the identifying feature of the system
    description.
    """

    allowed_oids = {
        ".1.3.6.1.2.1.1.1.0",  # system description
        ".1.3.6.1.2.1.1.2.0",  # system object ID
    }

    known_exceptions = {
        ".1.3.6.1.2.1.2.2.1.*": {"if", "inv_if"},
        ".1.3.6.1.2.1.25.1.1.0": {"hr_cpu", "hr_fs", "hr_ps"},
        ".1.3.6.1.2.1.31.1.1.1.6.*": {"if64", "if64adm"},
        ".1.3.6.1.2.1.43.*": {
            "printer_alerts",
            "printer_input",
            "printer_output",
            "printer_pages",
            "printer_supply",
        },
        ".1.3.6.1.2.1.47.1.1.1.1.*": {"snmp_extended_info"},
        ".1.3.6.1.2.1.105.1.3.1.1.*": {"pse_poe"},
        ".1.3.6.1.4.1.14848.2.1.1.1.0": {"etherbox"},
        ".1.3.6.1.4.1.2036.2.1.1.4.0": {"snmp_quantum_storage_info"},
        ".1.3.6.1.4.1.232.2.2.4.2.0": {
            "hp_proliant_cpu",
            "hp_proliant_da_cntlr",
            "hp_proliant_da_phydrv",
            "hp_proliant_fans",
            "hp_proliant_mem",
            "hp_proliant_power",
            "hp_proliant_psu",
            "hp_proliant_raid",
            "hp_proliant_systeminfo",
            "hp_proliant_temp",
            "hp_sts_drvbox",
        },
        ".1.3.6.1.4.1.30155.2.1.1.0": {"openbsd_sensors"},
        ".1.3.6.1.4.1.6302.2.1.1.1.0": {"emerson_stat", "emerson_temp"},
        ".1.3.6.1.4.1.674.*": {
            "dell_compellent_controller",
            "dell_compellent_disks",
            "dell_compellent_enclosure",
            "dell_compellent_folder",
            "dell_hw_info",
        },
    }

    for section in agent_based_plugins.snmp_sections.values():
        for (first_checked_oid, *_rest1), *_rest2 in (  #
            criterion
            for criterion in section.detect_spec
            if criterion  #
        ):
            if first_checked_oid in allowed_oids:
                continue
            assert str(section.name) in known_exceptions.get(first_checked_oid, ()), f"""
            If you've made it here, you have added a case to the known exceptions above.
            Even worse: You may have added an OID to the list of OIDs that are fetched
            from *all SNMP devices* known to the Checkmk site. Please reconsider!

            First OID fetched by {section.name}: {first_checked_oid}
            """


def test_snmp_section_parse_function_deals_with_empty_input(
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    """We make sure that all parse functions can handle empty table data"""

    def empty(l: int) -> list[list[list]]:
        return [[] for _ in range(l)]

    for section in agent_based_plugins.snmp_sections.values():
        _ = section.parse_function(empty(len(section.trees)))
