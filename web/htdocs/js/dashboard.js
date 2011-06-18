// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

function resize_dashlets(id, code)
{
    var resize_info = eval(code);

    for (var i in resize_info) {
        var dashlet = resize_info[i];

        // check if dashlet has title and resize its width
        var oDash = document.getElementById("dashlet_title_" + dashlet[0]);
        if (oDash) {
            oDash.style.width  = dashlet[3] + "px";
            oDash.style.top    = "-" + title_height + "px";
            oDash.style.height = title_height + "px";
        }

        // resize outer div
        var oDash = document.getElementById("dashlet_" + dashlet[0]);
        oDash.style.position = 'absolute';
        oDash.style.left   = dashlet[1] + "px";
        oDash.style.top    = dashlet[2] + "px";
        oDash.style.width  = dashlet[3] + "px";
        oDash.style.height = dashlet[4] + "px";

        // resize shadow images
        var oDash = document.getElementById("dashadow_w_" + dashlet[0]);
        oDash.style.height = (dashlet[4] - 32) + "px";
        var oDash = document.getElementById("dashadow_e_" + dashlet[0]);
        oDash.style.height = (dashlet[4] - 32) + "px";
        var oDash = document.getElementById("dashadow_n_" + dashlet[0]);
        oDash.style.width = (dashlet[3] - 32) + "px";
        var oDash = document.getElementById("dashadow_s_" + dashlet[0]);
        oDash.style.width = (dashlet[3] - 32) + "px";

        // resize content div
        var oDash = document.getElementById("dashlet_inner_" + dashlet[0]);
        oDash.style.position = 'absolute';
        oDash.style.left   = dashlet_padding + "px";
        oDash.style.top    = dashlet_padding + "px";
        oDash.style.width  = (dashlet[3] - 2*dashlet_padding) + "px";
        oDash.style.height = (dashlet[4] - 2*dashlet_padding) + "px";
    }
    oDash = null; 
}

function set_dashboard_size()
{
  var width = pageWidth();
  var height = pageHeight();
  oDash = document.getElementById("dashboard");
  oDash.style.position = 'absolute';
  oDash.style.left     = screen_margin + "px";
  oDash.style.top      = header_height + screen_margin + "px";
  oDash.style.width    = width - 2*screen_margin + "px";
  oDash.style.height   = height - 2*screen_margin - header_height + "px";

  ajax_url = 'dashboard_resize.py?name=' + dashboard_name 
           + '&width=' + width
           + '&height=' + height;
  get_url(ajax_url, resize_dashlets);
}

function dashboard_scheduler() {
    var timestamp = Date.parse(new Date()) / 1000;
    var newcontent = "";
    for (var i in refresh_dashlets) { 
        var nr      = refresh_dashlets[i][0];
        var refresh = refresh_dashlets[i][1];
        var url     = refresh_dashlets[i][2];

        if (timestamp % refresh == 0) {
            get_url(url, updateContents, "dashlet_inner_" + nr);
        }
    }
    // Detect page changes and re-register the mousemove event handler
    // in the content frame. another bad hack ... narf
    // LARS: Braucht man das Zeug hier auch?
    // if (contentFrameAccessible() && contentLocation != parent.frames[1].document.location) {
    //     registerEdgeListeners(parent.frames[1]);
    //     contentLocation = parent.frames[1].document.location;
    // }
    setTimeout(function() { dashboard_scheduler(); }, 1000);
}

function update_dashlet(id, code) {
  var obj = document.getElementById(id);
  if (obj) {
    obj.innerHTML = code;
    executeJS(id);
    obj = null;
  }
}
