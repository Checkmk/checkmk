/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

let width: number;
let height: number;
let netto_width: number;
let netto_height: number;
let from_time: number;
let until_time: number;
let v_min: number;
let v_max: number;
let canvas_id: string;

const left_border = 90;
const right_border = 50;
const top_border = 40;
const bottom_border = 50;

//TODO: It might be better to create a Graph class and make the above variables
//  its attributes?
export function create_graph(
    cid: string,
    ft: number,
    ut: number,
    vmi: number,
    vma: number,
) {
    // Keep important data as global variables, needed by
    // render_curve()
    canvas_id = cid;
    const canvas = <HTMLCanvasElement>document.getElementById(canvas_id);
    from_time = ft;
    until_time = ut;
    v_min = vmi;
    v_max = vma;

    width = canvas.width;
    height = canvas.height;
    netto_width = width - left_border - right_border;
    netto_height = height - top_border - bottom_border;
}

function arrow_up(
    c: CanvasRenderingContext2D,
    cx: number,
    cy: number,
    length: number,
    size: number,
    color: string,
) {
    c.strokeStyle = color;
    c.moveTo(cx, cy);
    c.lineTo(cx, cy - length);
    c.stroke();

    c.fillStyle = color;
    c.moveTo(cx - size / 2, cy - length);
    c.lineTo(cx + size / 2, cy - length);
    c.lineTo(cx, cy - size - length);
    c.fill();
}

function arrow_right(
    c: CanvasRenderingContext2D,
    cx: number,
    cy: number,
    length: number,
    size: number,
    color: string,
) {
    c.strokeStyle = color;
    c.moveTo(cx, cy);
    c.lineTo(cx + length, cy);
    c.stroke();

    c.fillStyle = color;
    c.moveTo(cx + length, cy - size / 2);
    c.lineTo(cx + length, cy + size / 2);
    c.lineTo(cx + length + size, cy);
    c.fill();
}

const linea = "#888888";
const lineb = "#bbbbbb";
const linec = "#bbbbbb";

export function render_coordinates(
    v_scala: [number, string][],
    t_scala: [number, string][],
) {
    // Create canvas
    const canvas = <HTMLCanvasElement>document.getElementById(canvas_id);
    const c = canvas.getContext("2d")!;
    c.font = "20px sans-serif";

    // Convert the coordinate system in a way, that we can directly
    // work with our native time and value.
    // x_scale = 1.0 * width / (until_time - from_time);
    // y_scale = 1.0 * -height / (v_max - v_min);
    // c.scale(x_scale, y_scale);
    // c.translate(-from_time, -v_max);

    let t;
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

    let i;
    c.fillStyle = "#000000";

    // Value scala (vertical)
    let val, txt, p, w;
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
    arrow_right(
        c,
        width - right_border,
        height - bottom_border,
        8,
        8,
        "#000000",
    );
}

function point(t: number, v: number): [number, number] {
    return [
        left_border +
            ((t - from_time) / (until_time - from_time)) * netto_width,
        height - bottom_border - ((v - v_min) / (v_max - v_min)) * netto_height,
    ];
}

function line(
    c: CanvasRenderingContext2D,
    t0: number,
    v0: number,
    t1: number,
    v1: number,
) {
    const p0 = point(t0, v0);
    const p1 = point(t1, v1);
    c.beginPath();
    c.moveTo(p0[0], p0[1]);
    c.lineTo(p1[0], p1[1]);
    c.stroke();
}

export function render_point(t: number, v: number, color: string) {
    const canvas = <HTMLCanvasElement>document.getElementById(canvas_id);
    const c = canvas.getContext("2d")!;
    const p = point(t, v);
    c.beginPath();
    c.lineWidth = 4;
    c.strokeStyle = color;
    c.moveTo(p[0] - 6, p[1] - 6);
    c.lineTo(p[0] + 6, p[1] + 6);
    c.moveTo(p[0] + 6, p[1] - 6);
    c.lineTo(p[0] - 6, p[1] + 6);
    c.stroke();
}

export function render_curve(
    points: number[],
    color: string,
    w: number,
    square: boolean,
) {
    const canvas = <HTMLCanvasElement>document.getElementById(canvas_id);
    const c = canvas.getContext("2d")!;

    c.beginPath();
    c.strokeStyle = color;
    c.lineWidth = w;

    let op;
    const time_step = (until_time - from_time) / points.length;
    let first = true;
    for (let i = 0; i < points.length; i++) {
        if (points[i] == null) {
            c.stroke();
            first = true;
            continue;
        }
        const p = point(from_time + time_step * i, points[i]);
        if (first) {
            c.moveTo(p[0], p[1]);
            first = false;
        } else {
            if (square && op) c.lineTo(p[0], op[1]);
            c.lineTo(p[0], p[1]);
        }
        op = p;
    }
    c.stroke();
}

export function render_area(points: number[], color: string, alpha: number) {
    render_dual_area(null, points, color, alpha);
}

export function render_area_reverse(
    points: number[],
    color: string,
    alpha: number,
) {
    render_dual_area(points, null, color, alpha);
}

export function render_dual_area(
    lower_points: null | number[],
    upper_points: null | number[],
    color: string,
    alpha: number,
) {
    const canvas = <HTMLCanvasElement>document.getElementById(canvas_id);
    const c = canvas.getContext("2d")!;

    c.fillStyle = color;
    c.globalAlpha = alpha;
    let num_points;
    if (lower_points) num_points = lower_points.length;
    else num_points = upper_points!.length;

    const time_step = (1.0 * (until_time - from_time)) / num_points;
    const pix_step = (1.0 * netto_width) / num_points;

    let x, yl, yu, h;
    for (let i = 0; i < num_points; i++) {
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
