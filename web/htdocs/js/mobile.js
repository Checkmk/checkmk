// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

/* Disable data-ajax per default, as it makes problems in most
   of our cases */

require("script-loader!../jquery/jquery-1.8.3.min.js");
require("script-loader!../jquery/jquery.mobile-1.2.1.min.js");

// Optional import is currently not possible using the ES6 imports
var graphs;
try {
    graphs = require("graphs");
} catch (e) {
    graphs = null;
}

$(document).ready(function () {
    $("a").attr("data-ajax", "false");
    $("form").attr("data-ajax", "false");
    $("div.error").addClass("ui-shadow");
    $("div.success").addClass("ui-shadow");
    $("div.really").addClass("ui-shadow");
    $("div.warning").addClass("ui-shadow");
});

$(document).bind("mobileinit", function () {
    $.mobile.ajaxEnabled = false;
    $.mobile.hashListeningEnabled = false;
});

export const cmk_export = {
    cmk: {
        graphs: graphs,
    },
};
