// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";

export function start_test(ident, hostname, transid) {
    var log = document.getElementById(ident + "_log");
    var img = document.getElementById(ident + "_img");
    var retry = document.getElementById(ident + "_retry");

    retry.style.display = "none";

    var vars = "";
    vars = "&_transid=" + encodeURIComponent(transid);
    vars +=
        "&ipaddress=" +
        encodeURIComponent(document.getElementsByName("vs_host_p_ipaddress")[0].value);

    if (document.getElementsByName("vs_host_p_snmp_community_USE")[0].checked)
        vars +=
            "&snmp_community=" +
            encodeURIComponent(document.getElementsByName("vs_host_p_snmp_community")[0].value);

    var v3_use;
    if (document.getElementsByName("vs_host_p_snmp_v3_credentials_USE")[0].checked) {
        v3_use = encodeURIComponent(
            document.getElementsByName("vs_host_p_snmp_v3_credentials_use")[0].value
        );
        vars += "&snmpv3_use=" + v3_use;
        if (v3_use == "0") {
            vars +=
                "&snmpv3_security_name=" +
                encodeURIComponent(
                    document.getElementsByName("vs_host_p_snmp_v3_credentials_0_1")[0].value
                );
        } else if (v3_use == "1") {
            vars +=
                "&snmpv3_auth_proto=" +
                encodeURIComponent(
                    document.getElementsByName("vs_host_p_snmp_v3_credentials_1_1")[0].value
                );
            vars +=
                "&snmpv3_security_name=" +
                encodeURIComponent(
                    document.getElementsByName("vs_host_p_snmp_v3_credentials_1_2")[0].value
                );
            vars +=
                "&snmpv3_security_password=" +
                encodeURIComponent(
                    document.getElementsByName("vs_host_p_snmp_v3_credentials_1_3")[0].value
                );
        } else if (v3_use == "2") {
            vars +=
                "&snmpv3_auth_proto=" +
                encodeURIComponent(
                    document.getElementsByName("vs_host_p_snmp_v3_credentials_2_1")[0].value
                );
            vars +=
                "&snmpv3_security_name=" +
                encodeURIComponent(
                    document.getElementsByName("vs_host_p_snmp_v3_credentials_2_2")[0].value
                );
            vars +=
                "&snmpv3_security_password=" +
                encodeURIComponent(
                    document.getElementsByName("vs_host_p_snmp_v3_credentials_2_3")[0].value
                );
            vars +=
                "&snmpv3_privacy_proto=" +
                encodeURIComponent(
                    document.getElementsByName("vs_host_p_snmp_v3_credentials_2_4")[0].value
                );
            vars +=
                "&snmpv3_privacy_password=" +
                encodeURIComponent(
                    document.getElementsByName("vs_host_p_snmp_v3_credentials_2_5")[0].value
                );
        }
    }

    vars +=
        "&agent_port=" +
        encodeURIComponent(document.getElementsByName("vs_rules_p_agent_port")[0].value);
    vars +=
        "&tcp_connect_timeout=" +
        encodeURIComponent(document.getElementsByName("vs_rules_p_tcp_connect_timeout")[0].value);
    vars +=
        "&snmp_timeout=" +
        encodeURIComponent(document.getElementsByName("vs_rules_p_snmp_timeout")[0].value);
    vars +=
        "&snmp_retries=" +
        encodeURIComponent(document.getElementsByName("vs_rules_p_snmp_retries")[0].value);

    img.src = img.src.replace(/(.*\/icon_).*(\.svg$)/i, "$1reload$2");
    utils.add_class(img, "reloading");

    log.innerHTML = "...";

    var data =
        "host=" + encodeURIComponent(hostname) + "&_test=" + encodeURIComponent(ident) + vars;

    ajax.call_ajax("wato_ajax_diag_host.py", {
        method: "POST",
        response_handler: handle_host_diag_result,
        handler_data: {hostname: hostname, ident: ident},
        post_data: data,
    });
}

function handle_host_diag_result(data, response_json) {
    var response = JSON.parse(response_json);

    var img = document.getElementById(data.ident + "_img");
    var log = document.getElementById(data.ident + "_log");
    var retry = document.getElementById(data.ident + "_retry");
    utils.remove_class(img, "reloading");

    var text = "";
    var new_icon = "";
    if (response.result_code == 1) {
        new_icon = "cancel";
        log.className = "log diag_failed";
        text = "API Error:" + response.result;
    } else {
        if (response.result.status_code == 1) {
            new_icon = "cancel";
            log.className = "log diag_failed";
        } else {
            new_icon = "accept";
            log.className = "log diag_success";
        }
        text = response.result.output;
    }

    img.src = img.src.replace(/(.*\/icon_).*(\.svg$)/i, "$1" + new_icon + "$2");
    log.innerText = text;

    retry.src = retry.src.replace(/(.*\/icon_).*(\.svg$)/i, "$1reload$2");
    retry.style.display = "inline";
    retry.parentNode.href =
        "javascript:cmk.host_diagnose.start_test('" +
        data.ident +
        "', '" +
        data.hostname +
        "', '" +
        response.result.next_transid +
        "');";
}
