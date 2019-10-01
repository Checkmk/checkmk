// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails.  You should have received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

import * as utils from "utils";
import * as ajax from "ajax";

export function start_test(ident, hostname, transid) {
    var log   = document.getElementById(ident + "_log");
    var img   = document.getElementById(ident + "_img");
    var retry = document.getElementById(ident + "_retry");

    retry.style.display = "none";

    var vars = "";
    vars = "&_transid=" + encodeURIComponent(transid);
    vars += "&ipaddress=" + encodeURIComponent(document.getElementsByName("vs_host_p_ipaddress")[0].value);


    if (document.getElementsByName("vs_host_p_snmp_community_USE")[0].checked)
        vars += "&snmp_community=" + encodeURIComponent(document.getElementsByName("vs_host_p_snmp_community")[0].value);

    var v3_use;
    if (document.getElementsByName("vs_host_p_snmp_v3_credentials_USE")[0].checked) {
        v3_use = encodeURIComponent(document.getElementsByName("vs_host_p_snmp_v3_credentials_use")[0].value);
        vars += "&snmpv3_use=" + v3_use;
        if (v3_use == "0") {
            vars += "&snmpv3_security_name=" + encodeURIComponent(document.getElementsByName("vs_host_p_snmp_v3_credentials_0_1")[0].value);
        }
        else if (v3_use == "1") {
            vars += "&snmpv3_auth_proto=" + encodeURIComponent(document.getElementsByName("vs_host_p_snmp_v3_credentials_1_1")[0].value);
            vars += "&snmpv3_security_name=" + encodeURIComponent(document.getElementsByName("vs_host_p_snmp_v3_credentials_1_2")[0].value);
            vars += "&snmpv3_security_password=" + encodeURIComponent(document.getElementsByName("vs_host_p_snmp_v3_credentials_1_3")[0].value);
        }
        else if (v3_use == "2") {
            vars += "&snmpv3_auth_proto=" + encodeURIComponent(document.getElementsByName("vs_host_p_snmp_v3_credentials_2_1")[0].value);
            vars += "&snmpv3_security_name=" + encodeURIComponent(document.getElementsByName("vs_host_p_snmp_v3_credentials_2_2")[0].value);
            vars += "&snmpv3_security_password=" + encodeURIComponent(document.getElementsByName("vs_host_p_snmp_v3_credentials_2_3")[0].value);
            vars += "&snmpv3_privacy_proto=" + encodeURIComponent(document.getElementsByName("vs_host_p_snmp_v3_credentials_2_4")[0].value);
            vars += "&snmpv3_privacy_password=" + encodeURIComponent(document.getElementsByName("vs_host_p_snmp_v3_credentials_2_5")[0].value);
        }
    }

    vars += "&agent_port=" + encodeURIComponent(document.getElementsByName("vs_rules_p_agent_port")[0].value);
    vars += "&tcp_connect_timeout=" + encodeURIComponent(document.getElementsByName("vs_rules_p_tcp_connect_timeout")[0].value);
    vars += "&snmp_timeout=" + encodeURIComponent(document.getElementsByName("vs_rules_p_snmp_timeout")[0].value);
    vars += "&snmp_retries=" + encodeURIComponent(document.getElementsByName("vs_rules_p_snmp_retries")[0].value);
    if (document.getElementsByName("vs_rules_p_datasource_program").length > 0) {
        vars += "&datasource_program=" + encodeURIComponent(document.getElementsByName("vs_rules_p_datasource_program")[0].value);
    }

    img.src = img.src.replace(/(.*\/icon_).*(\.png$)/i, "$1reload$2");
    utils.add_class(img, "reloading");

    log.innerHTML = "...";
    ajax.get_url("wato_ajax_diag_host.py?host=" + encodeURIComponent(hostname)
        + "&_test=" + encodeURIComponent(ident) + vars,
        handle_host_diag_result, { "hostname": hostname, "ident": ident }); // eslint-disable-line indent
}

function handle_host_diag_result(data, response_json) {
    var response = JSON.parse(response_json);

    var img   = document.getElementById(data.ident + "_img");
    var log   = document.getElementById(data.ident + "_log");
    var retry = document.getElementById(data.ident + "_retry");
    utils.remove_class(img, "reloading");

    var text = "";
    var new_icon = "";
    if (response.result_code == 1) {
        new_icon = "failed";
        log.className = "log diag_failed";
        text = "API Error:" + response.result;

    } else {
        if (response.result.status_code == 1) {
            new_icon = "failed";
            log.className = "log diag_failed";
        } else {
            new_icon = "success";
            log.className = "log diag_success";
        }
        text = response.result.output;
    }

    img.src = img.src.replace(/(.*\/icon_).*(\.png$)/i, "$1"+new_icon+"$2");
    log.innerText = text;

    retry.src = retry.src.replace(/(.*\/icon_).*(\.png$)/i, "$1reload$2");
    retry.style.display = "inline";
    retry.parentNode.href = "javascript:cmk.host_diagnose.start_test('"+data.ident+"', '"+data.hostname+"', '"+response.result.next_transid+"');";
}
