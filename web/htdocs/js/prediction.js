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

function render_prediction(canvas_id, data)
{
    var canvas = document.getElementById(canvas_id)
    var width = canvas.width;
    var height = canvas.height;
    var c = canvas.getContext('2d');
    var points = data["points"];
    c.fillStyle="#eeeeee";
    c.fillRect(0, 0, width-1, height-1);
    render_prediction_curve(c, width, height, points, 0, "#000000");
    render_prediction_curve(c, width, height, points, 1, "#00ff00");
    render_prediction_curve(c, width, height, points, 2, "#0000ff");

}

function render_prediction_curve(c, width, height, points, nr, color)
{
    var i;
    var x_scale = width / points.length;
    var y_scale = height / 5.0;
    c.beginPath();
    c.strokeStyle = color;
    c.moveTo(0, 0);
    for (i=0; i<points.length; i++) {
        var x = i * x_scale;
        var y = height - 1 - points[i][nr] * y_scale;
        c.lineTo(x, y);
    }
    c.stroke();
}
