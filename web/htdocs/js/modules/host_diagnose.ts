// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";

export function getFirstElementByNameAsInput(name: string): HTMLInputElement {
    return document.getElementsByName(name)[0] as HTMLInputElement;
}
export function start_test(ident, hostname, transid) {
    var log = document.getElementById(ident + "_log") as HTMLImageElement;
    var img = document.getElementById(ident + "_img") as HTMLImageElement;
    var retry = document.getElementById(ident + "_retry") as HTMLImageElement;

    retry!.style.display = "none";

    var vars = "";
    vars = "&_transid=" + encodeURIComponent(transid);
    vars +=
        "&ipaddress=" +
        encodeURIComponent(
            getFirstElementByNameAsInput("vs_host_p_ipaddress").value
        );

    if (getFirstElementByNameAsInput("vs_host_p_snmp_community_USE").checked)
        vars +=
            "&snmp_community=" +
            encodeURIComponent(
                getFirstElementByNameAsInput("vs_host_p_snmp_community").value
            );

    var v3_use;
    if (
        getFirstElementByNameAsInput("vs_host_p_snmp_v3_credentials_USE")
            .checked
    ) {
        v3_use = encodeURIComponent(
            getFirstElementByNameAsInput("vs_host_p_snmp_v3_credentials_use")
                .value
        );
        vars += "&snmpv3_use=" + v3_use;
        if (v3_use == "0") {
            vars +=
                "&snmpv3_security_name=" +
                encodeURIComponent(
                    getFirstElementByNameAsInput(
                        "vs_host_p_snmp_v3_credentials_0_1"
                    ).value
                );
        } else if (v3_use == "1") {
            vars +=
                "&snmpv3_auth_proto=" +
                encodeURIComponent(
                    getFirstElementByNameAsInput(
                        "vs_host_p_snmp_v3_credentials_1_1"
                    ).value
                );
            vars +=
                "&snmpv3_security_name=" +
                encodeURIComponent(
                    getFirstElementByNameAsInput(
                        "vs_host_p_snmp_v3_credentials_1_2"
                    ).value
                );
            vars +=
                "&snmpv3_security_password=" +
                encodeURIComponent(
                    getFirstElementByNameAsInput(
                        "vs_host_p_snmp_v3_credentials_1_3"
                    ).value
                );
        } else if (v3_use == "2") {
            vars +=
                "&snmpv3_auth_proto=" +
                encodeURIComponent(
                    getFirstElementByNameAsInput(
                        "vs_host_p_snmp_v3_credentials_2_1"
                    ).value
                );
            vars +=
                "&snmpv3_security_name=" +
                encodeURIComponent(
                    getFirstElementByNameAsInput(
                        "vs_host_p_snmp_v3_credentials_2_2"
                    ).value
                );
            vars +=
                "&snmpv3_security_password=" +
                encodeURIComponent(
                    getFirstElementByNameAsInput(
                        "vs_host_p_snmp_v3_credentials_2_3"
                    ).value
                );
            vars +=
                "&snmpv3_privacy_proto=" +
                encodeURIComponent(
                    getFirstElementByNameAsInput(
                        "vs_host_p_snmp_v3_credentials_2_4"
                    ).value
                );
            vars +=
                "&snmpv3_privacy_password=" +
                encodeURIComponent(
                    getFirstElementByNameAsInput(
                        "vs_host_p_snmp_v3_credentials_2_5"
                    ).value
                );
        }
    }

    vars +=
        "&agent_port=" +
        encodeURIComponent(
            getFirstElementByNameAsInput("vs_rules_p_agent_port").value
        );
    vars +=
        "&tcp_connect_timeout=" +
        encodeURIComponent(
            getFirstElementByNameAsInput("vs_rules_p_tcp_connect_timeout").value
        );
    vars +=
        "&snmp_timeout=" +
        encodeURIComponent(
            getFirstElementByNameAsInput("vs_rules_p_snmp_timeout").value
        );
    vars +=
        "&snmp_retries=" +
        encodeURIComponent(
            getFirstElementByNameAsInput("vs_rules_p_snmp_retries").value
        );

    img.src = img.src.replace(/(.*\/icon_).*(\.svg$)/i, "$1reload$2");
    utils.add_class(img, "reloading");

    log.innerHTML = "...";
    ajax.get_url(
        "wato_ajax_diag_host.py?host=" +
            encodeURIComponent(hostname) +
            "&_test=" +
            encodeURIComponent(ident) +
            vars,
        handle_host_diag_result,
        {hostname: hostname, ident: ident}
    ); // eslint-disable-line indent
}

function handle_host_diag_result(data, response_json) {
    var response = JSON.parse(response_json);

    var img = document.getElementById(data.ident + "_img") as HTMLImageElement;
    var log = document.getElementById(data.ident + "_log") as HTMLImageElement;
    var retry = document.getElementById(
        data.ident + "_retry"
    ) as HTMLImageElement;
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
    (retry.parentNode as HTMLAnchorElement).href =
        "javascript:cmk.host_diagnose.start_test('" +
        data.ident +
        "', '" +
        data.hostname +
        "', '" +
        response.result.next_transid +
        "');";
}
