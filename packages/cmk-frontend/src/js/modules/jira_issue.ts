/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import jQuery from "jquery";

window.jQuery = jQuery;

declare global {
    interface Window {
        ATL_JQ_PAGE_PROPS: any;
        jQuery: any;
    }
}

export function trigger_jira_collector() {
    jQuery.ajax({
        url: "https://support.checkmk.com/plugins/servlet/issueCollectorBootstrap.js?collectorId=6a1ec03f&locale=en_US",
        type: "get",
        cache: true,
        dataType: "script",
        success: function () {
            window.ATL_JQ_PAGE_PROPS = {
                triggerFunction: function (showCollectorDialog: () => void) {
                    showCollectorDialog();
                },
            };
        },
    });
}
