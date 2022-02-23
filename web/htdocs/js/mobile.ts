// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

/* Disable data-ajax per default, as it makes problems in most
   of our cases */

// NOTE: We use an up-to-date version of jQuery from the package-lock.json together
// with a patched version of jQuery mobile to make it compatible with jQuery:
// https://github.com/jquery/jquery-mobile/issues/8662#issuecomment-687738965
require("script-loader!jquery");
require("script-loader!../jquery/jquery.mobile-1.4.5.min.js");

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
    $["mobile"].ajaxEnabled = false;
    $["mobile"].hashListeningEnabled = false;
});

// Never allow the mobile page to be opened in an iframe. Redirect top page to the current content page.
// This will result in a full screen mobile interface page.
if (top != self) {
    window.top.location.href = location.toString();
}

$(document).ready(function () {
    $("a").click(function (event) {
        event.preventDefault();
        window.location.href = $(this).attr("href") as string;
    });
});

export const cmk_export = {
    cmk: {
        graphs: graphs,
    },
};
