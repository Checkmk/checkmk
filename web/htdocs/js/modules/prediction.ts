// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

var width;
var height;
var netto_width;
var netto_height;
var from_time;
var until_time;
var v_min;
var v_max;
var canvas_id;

var left_border = 90;
var right_border = 50;
var top_border = 40;
var bottom_border = 50;

export function create_graph(cid, ft, ut, vmi, vma) {
    // Keep important data as global variables, needed by
    // render_curve()
    canvas_id = cid;
    var canvas =<HTMLCanvasElement> document.getElementById(canvas_id);
    from_time = ft;
    until_time = ut;
    v_min = vmi;
    v_max = vma;

    width = canvas.width;
    height = canvas.height;
    netto_width = width - left_border - right_border;
    netto_height = height - top_border - bottom_border;
}

function arrow_up(c, cx, cy, length, size, color) {
    c.strokeStyle = color;
    c.moveTo(cx, cy);
    c.lineTo(cx, cy - length);
    c.stroke();

    c.fillColor = color;
    c.moveTo(cx - size / 2, cy - length);
    c.lineTo(cx + size / 2, cy - length);
    c.lineTo(cx, cy - size - length);
    c.fill();
}

function arrow_right(c, cx, cy, length, size, color) {
    c.strokeStyle = color;
    c.moveTo(cx, cy);
    c.lineTo(cx + length, cy);
    c.stroke();

    c.fillColor = color;
    c.moveTo(cx + length, cy - size / 2);
    c.lineTo(cx + length, cy + size / 2);
    c.lineTo(cx + length + size, cy);
    c.fill();
}

var linea = "#888888";
var lineb = "#bbbbbb";
var linec = "#bbbbbb";

export function render_coordinates(v_scala, t_scala) {
    // Create canvas
    var canvas = <HTMLCanvasElement>document.getElementById(canvas_id);
    var c = canvas.getContext("2d");
    c.font = "20px sans-serif";

    // Convert the coordinate system in a way, that we can directly
    // work with our native time and value.
    // x_scale = 1.0 * width / (until_time - from_time);
    // y_scale = 1.0 * -height / (v_max - v_min);
    // c.scale(x_scale, y_scale);
    // c.translate(-from_time, -v_max);

    var t;
    c.strokeStyle = linec;
    c.lineWidth = 0.5;
    for (t = from_time; t <= until_time; t += 1800) {
        if (t % 7200 == 0) c.strokeStyle = linea;
        else if (t % 3600 == 0) c.strokeStyle = lineb;
        else c.strokeStyle = linec;
        line(c, t, v_min, t, v_max);
    }

    c.strokeStyle = lineb;
    c.lineWidth = 1;
    for (t = from_time; t <= until_time; t += 7200) {
        line(c, t, v_min, t, v_max);
    }

    var i;
    c.fillStyle = "#000000";

    // Value scala (vertical)
    var val, txt, p, w;
    for (i = 0; i < v_scala.length; i++) {
        val = v_scala[i][0];
        txt = v_scala[i][1];
        p = point(0, val);
        w = c.measureText(txt).width;
        c.fillText(txt, left_border - w - 16, p[1] + 6);
        if (i % 2) c.strokeStyle = lineb;
        else c.strokeStyle = linea;
        line(c, from_time, val, until_time, val);
    }

    // Time scala (horizontal)
    for (i = 0; i < t_scala.length; i++) {
        t = t_scala[i][0];
        txt = t_scala[i][1];
        p = point(t, 0);
        w = c.measureText(txt).width;
        c.fillText(txt, p[0] - w / 2, height - bottom_border + 28);
        if (i % 2) c.strokeStyle = lineb;
        else c.strokeStyle = linea;
    }

    // Paint outlines and arrows
    c.strokeStyle = "#000000";
    line(c, from_time, 0, until_time, 0);
    line(c, from_time, v_min, from_time, v_max);
    line(c, from_time, v_min, until_time, v_min);
    arrow_up(c, left_border, top_border, 1, 8, "#000000");
    arrow_right(c, width - right_border, height - bottom_border, 8, 8, "#000000");
}

function point(t, v) {
    return [
        left_border + ((t - from_time) / (until_time - from_time)) * netto_width,
        height - bottom_border - ((v - v_min) / (v_max - v_min)) * netto_height,
    ];
}

function line(c, t0, v0, t1, v1) {
    var p0 = point(t0, v0);
    var p1 = point(t1, v1);
    c.beginPath();
    c.moveTo(p0[0], p0[1]);
    c.lineTo(p1[0], p1[1]);
    c.stroke();
}

export function render_point(t, v, color) {
    var canvas = <HTMLCanvasElement>document.getElementById(canvas_id);
    var c = canvas.getContext("2d");
    var p = point(t, v);
    c.beginPath();
    c.lineWidth = 4;
    c.strokeStyle = color;
    c.moveTo(p[0] - 6, p[1] - 6);
    c.lineTo(p[0] + 6, p[1] + 6);
    c.moveTo(p[0] + 6, p[1] - 6);
    c.lineTo(p[0] - 6, p[1] + 6);
    c.stroke();
}

export function render_curve(points, color, w, square) {
    var canvas = <HTMLCanvasElement>document.getElementById(canvas_id);
    var c = canvas.getContext("2d");

    c.beginPath();
    c.strokeStyle = color;
    c.lineWidth = w;

    var op;
    var time_step = (until_time - from_time) / points.length;
    var first = true;
    for (var i = 0; i < points.length; i++) {
        if (points[i] == null) {
            c.stroke();
            first = true;
            continue;
        }
        var p = point(from_time + time_step * i, points[i]);
        if (first) {
            c.moveTo(p[0], p[1]);
            first = false;
        } else {
            if (square) c.lineTo(p[0], op[1]);
            c.lineTo(p[0], p[1]);
        }
        op = p;
    }
    c.stroke();
}

export function render_area(points, color, alpha) {
    render_dual_area(null, points, color, alpha);
}

export function render_area_reverse(points, color, alpha) {
    render_dual_area(points, null, color, alpha);
}

export function render_dual_area(lower_points, upper_points, color, alpha) {
    var canvas = <HTMLCanvasElement>document.getElementById(canvas_id);
    var c = canvas.getContext("2d");

    c.fillStyle = color;
    c.globalAlpha = alpha;
    var num_points;
    if (lower_points) num_points = lower_points.length;
    else num_points = upper_points.length;

    var time_step = (1.0 * (until_time - from_time)) / num_points;
    var pix_step = (1.0 * netto_width) / num_points;

    var x, yl, yu, h;
    for (var i = 0; i < num_points; i++) {
        x = point(from_time + time_step * i, 0)[0];
        if (lower_points) yl = point(0, lower_points[i])[1];
        else yl = height - bottom_border;

        if (upper_points) yu = point(0, upper_points[i])[1];
        else yu = top_border;
        h = yu - yl;
        c.fillRect(x, yl, pix_step, h);
    }
    c.globalAlpha = 1;
}
