// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

    var oDash = null;
    for (var i in resize_info) {
        var dashlet = resize_info[i];
        var d_number  = dashlet[0];
        var d_visible = dashlet[1];
        var d_left    = dashlet[2];
        var d_top     = dashlet[3];
        var d_width   = dashlet[4];
        var d_height  = dashlet[5];

        var disstyle = "block";
        if (!d_visible) {
            disstyle = "none";
        }

        // check if dashlet has title and resize its width
        oDash = document.getElementById("dashlet_title_" + d_number);
        if (oDash) {
            //if browser window to small prevent js error
            if(d_width <= 20){
                d_width = 21;
            }
            oDash.style.width  = d_width - 20 + "px";
            /* oDash.style.top    = "-" + title_height + "px";
            oDash.style.height = title_height + "px"; */
            oDash.style.display = disstyle;
        }

        // resize outer div
        oDash = document.getElementById("dashlet_" + d_number);
        if(oDash) {
            oDash.style.position = 'absolute';
            oDash.style.display  = disstyle;
            oDash.style.left     = d_left + "px";
            oDash.style.top      = d_top + "px";
            oDash.style.width    = d_width + "px";
            oDash.style.height   = d_height + "px";
        }

        // resize shadow images
        var netto_height = d_height - dashlet_padding[0] - dashlet_padding[2];
        var netto_width  = d_width  - dashlet_padding[1] - dashlet_padding[3];

        var oShadow;
        oShadow = document.getElementById("dashadow_w_" + d_number);
        if (oShadow) oShadow.style.display  = disstyle;
        if (oShadow && d_height - 32 > 0)
            oShadow.style.height = netto_height + "px";

        oShadow = document.getElementById("dashadow_e_" + d_number);
        if (oShadow) oShadow.style.display  = disstyle;
        if (oShadow && d_height - 32 > 0)
            oShadow.style.height = netto_height + "px";

        oShadow = document.getElementById("dashadow_n_" + d_number);
        if (oShadow) oShadow.style.display  = disstyle;
        if (oShadow && d_width - 32 > 0)
            oShadow.style.width = netto_width - corner_overlap + "px";

        oShadow = document.getElementById("dashadow_s_" + d_number);
        if (oShadow) oShadow.style.display  = disstyle;
        if (oShadow && d_width - 32 > 0)
            oShadow.style.width = netto_width - corner_overlap + "px";

        // resize content div
        oDash = document.getElementById("dashlet_inner_" + d_number);
        if(oDash) {
            oDash.style.display  = disstyle;
            oDash.style.position = 'absolute';
            oDash.style.left   = dashlet_padding[3] + "px";
            oDash.style.top    = dashlet_padding[0] + "px";
            if (netto_width > 0)
                oDash.style.width  = netto_width + "px";
            if (netto_height > 0)
                oDash.style.height = netto_height + "px";
        }
    }
    oDash = null;
}

function set_dashboard_size()
{
  var body_padding = 5;
  var width  = pageWidth();
  var height = pageHeight();
  width  = width - 2*screen_margin - 2*body_padding;
  height = height - 2*screen_margin - header_height - body_padding;

  oDash = document.getElementById("dashboard");
  oDash.style.position = 'absolute';
  oDash.style.left     = screen_margin + "px";
  oDash.style.top      = (header_height + screen_margin) + "px";
  oDash.style.width    = width + "px";
  oDash.style.height   = height + "px";

  ajax_url = 'dashboard_resize.py?name=' + dashboard_name
           + '&width=' + width
           + '&height=' + height;
  get_url(ajax_url, resize_dashlets);
}

function dashboard_scheduler(force) {
    var timestamp = Date.parse(new Date()) / 1000;
    var newcontent = "";
    for(var i = 0; i < refresh_dashlets.length; i++) {
        var nr      = refresh_dashlets[i][0];
        var refresh = refresh_dashlets[i][1];
        var url     = refresh_dashlets[i][2];

        if (force || (refresh > 0 && timestamp % refresh == 0)) {
            get_url(url, dashboard_update_contents, "dashlet_inner_" + nr);
        }
    }
    setTimeout(function() { dashboard_scheduler(0); }, 1000);
}

function dashboard_update_contents(id, code) {
    // Update the header time
    updateHeaderTime();

    // Call the generic function to replace the dashlet inner code
    updateContents(id, code);
}

function update_dashlet(id, code) {
  var obj = document.getElementById(id);
  if (obj) {
    obj.innerHTML = code;
    executeJS(id);
    obj = null;
  }
}
