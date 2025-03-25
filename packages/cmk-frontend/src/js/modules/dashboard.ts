/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {call_ajax} from "./ajax";
import {confirm_dialog} from "./forms";
import {
    add_class,
    add_event_handler,
    browser,
    get_button,
    get_theme,
    has_class,
    is_window_active,
    makeuri,
    makeuri_contextless,
    page_height,
    page_width,
    prevent_default_events,
    reload_whole_page,
    remove_class,
    update_contents,
    update_header_timer,
    update_url_parameter,
} from "./utils";

interface Dashlet {
    x: number;
    y: number;
    w: number;
    h: number;
}

/*
 * information about DashboardProperties type
 * we got the data from cmk/gui/dashboard.py
 * since cmk.dashboard.set_dashboard_properties(%s) is being called there.
 * refresh_Dashlets[2] it was tricky a bit since it could be
 * none or string (url) or function the responsible function
 * is get_refresh_action() in cmk/gui/plugins/dashboard/utils.py:
 * */
interface DashboardProperties<T> {
    MAX: number;
    GROW: number;
    grid_size: number;
    dashlet_padding: [number, number, number, number, number];
    dashlet_min_size: [number, number];
    refresh_dashlets: [number, number, T][];
    on_resize_dashlets: Record<number, T | undefined>;
    dashboard_name: string;
    dashboard_mtime: number;
    dashlets: Dashlet[];
    slim_editor_thresholds: Thresholds;
}

type DashboardPropertiesAPI = DashboardProperties<string>;
type DashboardPropertiesGlobal = DashboardProperties<string | (() => void)>;

interface GDrag {
    m_x: number;
    m_y: number;
    x: number;
    y: number;
    w: number;
    h: number;
}

interface Thresholds {
    height: number;
    width: number;
}

const reload_on_resize: Record<number, any> = {};
export let dashboard_properties = {} as DashboardPropertiesGlobal;

// Set the dashboard as a start URL for the user
export function set_start_url(dashboard_name: string) {
    call_ajax(
        "ajax_set_dashboard_start_url.py?name=" +
            encodeURIComponent(dashboard_name),
        {
            response_handler: (_handler_data: any, response_body: string) => {
                const response = JSON.parse(response_body);
                if (response.result_code === 0) {
                    reload_whole_page();
                } else {
                    confirm_dialog(
                        {
                            text: response.result,
                            confirmButtonText: "OK",
                            showCancelButton: false,
                        },
                        null,
                    );
                }
            },
            method: "POST",
        },
    );
}

export function set_reload_on_resize(dashlet_id: number, url: string) {
    reload_on_resize[dashlet_id] = url;
}

//the python side returns a json which includes javascript code.
// this javascript code is encoded as string, so we need to eval
// this string in order to make it executable on the javascript side.
// but there is more: it could also be possible that the value is not
// a javascript function, but a literal string. in this case the value
// is encoded twice: "\"litera_string\"".
export function set_dashboard_properties(properties: DashboardPropertiesAPI) {
    dashboard_properties = properties;
    const {refresh_dashlets, on_resize_dashlets, ...others} = properties;
    // HACK: We JSON-encode refresh/resize actions twice, so undo one layer here...

    const tmp_refresh_dashlets = refresh_dashlets.map<
        [number, number, string | (() => void)]
        /* eslint-disable-next-line no-eval -- Highlight existing violations CMK-17846 */
    >(elem => [elem[0], elem[1], eval(elem[2])]);

    const tmp_on_resize_dashlets: Record<
        number,
        string | undefined | (() => void)
    > = {};
    for (const key in on_resize_dashlets) {
        /* eslint-disable-next-line no-eval -- Highlight existing violations CMK-17846 */
        tmp_on_resize_dashlets[key] = eval(on_resize_dashlets[key]!);
    }

    dashboard_properties = {
        refresh_dashlets: tmp_refresh_dashlets,
        on_resize_dashlets: tmp_on_resize_dashlets,
        ...others,
    };
}

function size_dashlets() {
    const size_info = calculate_dashlets();
    let oDash: HTMLElement | null = null;
    let oDashTitle: HTMLElement | null = null;
    let oDashInner: HTMLElement | null = null;
    let oDashControls: HTMLElement | null = null;

    for (let d_number = 0; d_number < size_info.length; d_number++) {
        const dashlet: number[] = size_info[d_number];
        const d_left = dashlet[0];
        const d_top = dashlet[1];
        let d_width = dashlet[2];
        const d_height = dashlet[3];
        const disstyle = "block";

        // check if dashlet has title and resize its width
        oDashTitle = document.getElementById("dashlet_title_" + d_number);

        const has_title = Boolean(oDashTitle);
        if (has_title) {
            oDashTitle = oDashTitle!;
            //if browser window to small prevent js error
            if (d_width <= 20) {
                d_width = 21;
            }
            oDashTitle.style.width = d_width - 17 + "px"; // 9 title padding + empty space on right of dashlet
            oDashTitle.style.display = disstyle;
            oDashTitle.style.left =
                dashboard_properties.dashlet_padding[3] + "px";
            oDashTitle.style.top =
                dashboard_properties.dashlet_padding[4] + "px";
        }

        // resize outer div
        oDash = document.getElementById("dashlet_" + d_number);
        if (oDash) {
            oDash.style.display = disstyle;
            oDash.style.left = d_left + "px";
            oDash.style.top = d_top + "px";
            oDash.style.width = d_width + "px";
            oDash.style.height = d_height + "px";
        }

        let top_padding = dashboard_properties.dashlet_padding[0];
        if (!has_title) top_padding = dashboard_properties.dashlet_padding[4];

        const netto_height =
            d_height - top_padding - dashboard_properties.dashlet_padding[2];
        const netto_width =
            d_width -
            dashboard_properties.dashlet_padding[1] -
            dashboard_properties.dashlet_padding[3];

        // resize content div
        oDashInner = document.getElementById("dashlet_inner_" + d_number);
        if (oDashInner) {
            oDashInner.style.display = disstyle;

            const old_width = oDashInner.clientWidth;
            const old_height = oDashInner.clientHeight;

            oDashInner.style.left =
                dashboard_properties.dashlet_padding[3] + "px";
            oDashInner.style.top = top_padding + "px";
            if (!has_title) {
                oDashInner.style.top = top_padding + "px";
            }
            if (netto_width > 0) oDashInner.style.width = netto_width + "px";
            if (netto_height > 0) {
                oDashInner.style.height = netto_height + "px";
                if (!has_title) {
                    oDashInner.style.height = netto_height + "px";
                }
            }

            if (
                old_width != oDashInner.clientWidth ||
                old_height != oDashInner.clientHeight
            ) {
                if (
                    !g_resizing ||
                    parseInt(
                        (
                            (g_resizing as HTMLElement).parentNode!
                                .parentNode as HTMLElement
                        ).id.replace("dashlet_", ""),
                    ) != d_number
                ) {
                    dashlet_resized(d_number, oDashInner);
                }
            }
        }

        // resize controls container when in edit mode
        oDashControls = document.getElementById("dashlet_controls_" + d_number);
        if (oDashControls) {
            set_control_size(oDashControls, d_width, d_height);
        }
    }
}

export function adjust_single_metric_font_size(
    oTdMetricValue: HTMLTableCellElement,
) {
    const originalFontSize = parseFloat(oTdMetricValue.style.fontSize);
    const oAMetricValue = oTdMetricValue.childNodes[0] as HTMLAnchorElement;
    if (oAMetricValue.scrollWidth > (oTdMetricValue.clientWidth * 9) / 10)
        oTdMetricValue.style.fontSize = (originalFontSize * 9) / 10 + "px";
    else
        oTdMetricValue.style.fontSize =
            (oTdMetricValue.clientHeight * 4) / 5 + "px";

    if (oAMetricValue.scrollWidth > (oTdMetricValue.clientWidth * 9) / 10)
        adjust_single_metric_font_size(oTdMetricValue);
}

function set_control_size(
    dash_controls: HTMLElement,
    width: number,
    height: number,
) {
    dash_controls.style.width =
        width -
        dashboard_properties.dashlet_padding[1] -
        dashboard_properties.dashlet_padding[3] +
        "px";
    dash_controls.style.height =
        height -
        dashboard_properties.dashlet_padding[2] -
        dashboard_properties.dashlet_padding[4] +
        "px";
    dash_controls.style.left = dashboard_properties.dashlet_padding[3] + "px";
    dash_controls.style.top = dashboard_properties.dashlet_padding[4] + "px";
}

function is_dynamic(x: number) {
    return x == dashboard_properties.MAX || x == dashboard_properties.GROW;
}

function align_to_grid(px: number) {
    return (
        ~~(px / dashboard_properties.grid_size) * dashboard_properties.grid_size
    );
}

class Vec {
    x: number;
    y: number;

    constructor(x: number | null, y: number | null) {
        this.x = x || 0;
        this.y = y || 0;
    }

    divide(s: number) {
        return new Vec(~~(this.x / s), ~~(this.y / s));
    }

    add(v: Vec) {
        return new Vec(this.x + v.x, this.y + v.y);
    }

    make_absolute(size_v: Vec) {
        return new Vec(
            this.x < 0 ? this.x + size_v.x + 1 : this.x - 1,
            this.y < 0 ? this.y + size_v.y + 1 : this.y - 1,
        );
    }

    // Compute the initial size of the dashlet. If dashboard_properties.MAX is used,
    // then the dashlet consumes all space in its growing direction,
    // regardless of any other dashlets.
    initial_size(pos_v: Vec, grid_v: Vec) {
        return new Vec(
            this.x == dashboard_properties.MAX
                ? grid_v.x - Math.abs(pos_v.x) + 1
                : this.x == dashboard_properties.GROW
                  ? dashboard_properties.dashlet_min_size[0]
                  : this.x,
            this.y == dashboard_properties.MAX
                ? grid_v.y - Math.abs(pos_v.y) + 1
                : this.y == dashboard_properties.GROW
                  ? dashboard_properties.dashlet_min_size[1]
                  : this.y,
        );
    }

    // return codes:
    //  0: absolute size, no growth
    //  1: grow direction right, down
    // -1: grow direction left, up
    compute_grow_by(size_v: Vec) {
        return new Vec(
            size_v.x != dashboard_properties.GROW ? 0 : this.x < 0 ? -1 : 1,
            size_v.y != dashboard_properties.GROW ? 0 : this.y < 0 ? -1 : 1,
        );
    }

    toString() {
        return this.x + "/" + this.y;
    }
}

function calculate_dashlets() {
    const screen_size = new Vec(g_dashboard_width, g_dashboard_height);
    const raster_size = screen_size.divide(dashboard_properties.grid_size);
    const used_matrix: Record<string, boolean> = {};
    let positions: [number, number, number, number, Vec][] = [];

    // first place all dashlets at their absolute positions
    let nr: number,
        top: number,
        left: number,
        right: number,
        bottom: number,
        grow_by: Vec;
    for (nr = 0; nr < dashboard_properties.dashlets.length; nr++) {
        const dashlet = dashboard_properties.dashlets[nr];

        // Relative position is as noted in the declaration. 1,1 => top left origin,
        // -1,-1 => bottom right origin, 0 is not allowed here
        // starting from 1, negative means: from right/bottom
        const rel_position = new Vec(dashlet.x, dashlet.y);

        // Compute the absolute position, this time from 0 to raster_size-1
        const abs_position = rel_position.make_absolute(raster_size);

        // The size in raster-elements. A 0 for a dimension means growth. No negative values here.
        const size = new Vec(dashlet.w, dashlet.h);

        // Compute the minimum used size for the dashlet. For growth-dimensions we start with 1
        const used_size = size.initial_size(rel_position, raster_size);

        // Now compute the rectangle that is currently occupied. The coords
        // of bottomright are *not* included.
        if (rel_position.x > 0) {
            left = abs_position.x;
            right = left + used_size.x;
        } else {
            right = abs_position.x;
            left = right - used_size.x;
        }

        if (rel_position.y > 0) {
            top = abs_position.y;
            bottom = top + used_size.y;
        } else {
            bottom = abs_position.y;
            top = bottom - used_size.y;
        }

        // Allocate used squares in matrix. If not all squares we need are free,
        // then the dashboard is too small for all dashlets (as it seems).
        for (let x = left; x < right; x++) {
            for (let y = top; y < bottom; y++) {
                used_matrix[x + " " + y] = true;
            }
        }
        // Helper variable for how to grow, both x and y in [-1, 0, 1]
        grow_by = rel_position.compute_grow_by(size);

        positions.push([left, top, right, bottom, grow_by]);
    }

    const try_allocate = function (
        left: number,
        top: number,
        right: number,
        bottom: number,
    ) {
        let x, y;
        // Try if all needed squares are free
        for (x = left; x < right; x++)
            for (y = top; y < bottom; y++)
                if (x + " " + y in used_matrix) return false;

        // Allocate all needed squares
        for (x = left; x < right; x++)
            for (y = top; y < bottom; y++) used_matrix[x + " " + y] = true;

        return true;
    };

    // Now try to expand all elastic rectangles as far as possible
    // FIXME: Das hier muesste man optimieren
    let at_least_one_expanded = true;
    while (at_least_one_expanded) {
        at_least_one_expanded = false;
        const new_positions: [number, number, number, number, Vec][] = [];
        for (nr = 0; nr < positions.length; nr++) {
            left = positions[nr][0];
            top = positions[nr][1];
            right = positions[nr][2];
            bottom = positions[nr][3];
            grow_by = positions[nr][4];

            // try to grow in X direction by one
            if (
                grow_by.x > 0 &&
                right < raster_size.x &&
                try_allocate(right, top, right + 1, bottom)
            ) {
                at_least_one_expanded = true;
                right += 1;
            } else if (
                grow_by.x < 0 &&
                left > 0 &&
                try_allocate(left - 1, top, left, bottom)
            ) {
                at_least_one_expanded = true;
                left -= 1;
            }

            // try to grow in Y direction by one
            if (
                grow_by.y > 0 &&
                bottom < raster_size.y &&
                try_allocate(left, bottom, right, bottom + 1)
            ) {
                at_least_one_expanded = true;
                bottom += 1;
            } else if (
                grow_by.y < 0 &&
                top > 0 &&
                try_allocate(left, top - 1, right, top)
            ) {
                at_least_one_expanded = true;
                top -= 1;
            }
            new_positions.push([left, top, right, bottom, grow_by]);
        }
        positions = new_positions;
    }

    const size_info: number[][] = [];
    for (nr = 0; nr < positions.length; nr++) {
        left = positions[nr][0];
        top = positions[nr][1];
        right = positions[nr][2];
        bottom = positions[nr][3];
        size_info.push([
            left * dashboard_properties.grid_size,
            top * dashboard_properties.grid_size,
            (right - left) * dashboard_properties.grid_size,
            (bottom - top) * dashboard_properties.grid_size,
        ]);
    }
    return size_info;
}

let g_dashboard_resizer: null | boolean = null;
let g_dashboard_top: number | null = null;
let g_dashboard_left: number | null = null;
let g_dashboard_width: number | null = null;
let g_dashboard_height: number | null = null;

export function calculate_dashboard() {
    if (g_dashboard_resizer !== null) return; // another resize is processed
    g_dashboard_resizer = true;

    const oDash = document.getElementById("dashboard");
    if (!oDash) throw new Error("oDash shouldn't be null!");
    const dashboard_rect = oDash.getBoundingClientRect();

    g_dashboard_top = dashboard_rect.top;
    g_dashboard_left = dashboard_rect.left;
    g_dashboard_width = (page_width() || 0) - g_dashboard_left;
    g_dashboard_height = (page_height() || 0) - g_dashboard_top;
    oDash.style.width = g_dashboard_width + "px";
    oDash.style.height = g_dashboard_height + "px";

    size_dashlets();
    g_dashboard_resizer = null;
}

export function execute_dashboard_scheduler(initial: number) {
    // Stop reload of the dashlets in case the browser window / tab is not visible
    // for the user. Retry after short time.
    if (!is_window_active()) {
        setTimeout(function () {
            execute_dashboard_scheduler(initial);
        }, 250);
        return;
    }

    const timestamp = Math.trunc(new Date().getTime() / 1000);
    for (let i = 0; i < dashboard_properties.refresh_dashlets.length; i++) {
        const nr = dashboard_properties.refresh_dashlets[i][0];
        const refresh = dashboard_properties.refresh_dashlets[i][1];
        let url = dashboard_properties.refresh_dashlets[i][2];

        if (
            (initial &&
                document.getElementById("dashlet_inner_" + nr)?.innerHTML ==
                    "") ||
            (refresh > 0 && timestamp % refresh == 0)
        ) {
            if (typeof url === "string") {
                if (url.indexOf("?") !== -1)
                    url += "&mtime=" + dashboard_properties.dashboard_mtime;
                else url += "?mtime=" + dashboard_properties.dashboard_mtime;
                call_ajax(url, {
                    response_handler: dashboard_update_contents,
                    handler_data: "dashlet_inner_" + nr,
                });
            } else {
                url(); // Execute "on_refresh" javascript function
            }
        }
    }

    // Update timestamp every minute
    // Required if there are no refresh_dashlets present or all refresh times are > 60sec
    if (timestamp % 60 == 0) update_header_timer();

    setTimeout(function () {
        execute_dashboard_scheduler(0);
    }, 1000);
}

function dashboard_update_contents(id: string, response_text: string) {
    update_header_timer();

    // Call the generic function to replace the dashlet inner code
    update_contents(id, response_text);
}

//
// DASHBOARD EDITING
//

let g_editing = false;

export function toggle_dashboard_edit(
    edit_text?: string,
    display_text?: string,
) {
    g_editing = !g_editing;

    // Toggle the page menu elements
    const toggle_suggestion = document.getElementById(
        "menu_suggestion_toggle_edit",
    );
    const toggle_shortcut = document.getElementById(
        "menu_shortcut_toggle_edit",
    );
    const toggle_entry = document.getElementById("menu_entry_toggle_edit");

    if (edit_text && display_text) {
        const title = g_editing ? edit_text : display_text;
        if (toggle_suggestion) toggle_suggestion.lastChild!.textContent = title;
        toggle_shortcut!.title = title;
        toggle_entry!.firstChild!.lastChild!.textContent = title;
    }

    if (g_editing) {
        const icon_disable =
            "themes/" + get_theme() + "/images/emblem_disable.svg";
        if (toggle_suggestion)
            (
                toggle_suggestion.querySelector(
                    "img.emblem",
                ) as HTMLImageElement
            ).src = icon_disable;
        (toggle_shortcut!.querySelector("img.emblem") as HTMLImageElement).src =
            icon_disable;
        (toggle_entry!.querySelector("img.emblem") as HTMLImageElement).src =
            icon_disable;
    } else {
        const icon_trans = "themes/facelift/images/emblem_trans.svg";
        if (toggle_suggestion)
            (
                toggle_suggestion.querySelector(
                    "img.emblem",
                ) as HTMLImageElement
            ).src = icon_trans;
        (toggle_shortcut!.querySelector("img.emblem") as HTMLImageElement).src =
            icon_trans;
        (toggle_entry!.querySelector("img.emblem") as HTMLImageElement).src =
            icon_trans;
    }

    const dashlet_divs = document.getElementsByClassName(
        "dashlet",
    ) as HTMLCollectionOf<HTMLElement>;
    for (let i = 0; i < dashlet_divs.length; i++)
        dashlet_toggle_edit(dashlet_divs[i]);

    // Remove/Add edit=1 parameter from URL to make page reload handling correct
    update_url_parameter("edit", g_editing ? "1" : "0");

    toggle_grid();
}

function toggle_grid() {
    if (!g_editing) {
        remove_class(document.getElementById("dashboard"), "grid");
    } else {
        add_class(document.getElementById("dashboard"), "grid");
    }
}

// The resize controls are transparent areas at the border of the
// snapin which give the user the option to dragresize the dashlets
// in the dimension where absolute sizes are to be used.
//
// render top/bottom or left/right areas depending on dimension i
function render_resize_controls(controls: HTMLElement, i: number) {
    for (let a = 0; a < 2; a++) {
        const resize = document.createElement("div");
        resize.className = "resize resize" + i + " resize" + i + "_" + a;
        controls.appendChild(resize);
        const indication = document.createElement("div");
        indication.className =
            "resize resize" + i + " resize" + i + "_" + a + " circle_handle";
        const resize_image = document.createElement("div");
        resize_image.className = "resize_image";
        indication.appendChild(resize_image);
        controls.appendChild(indication);
    }
}

function render_sizer(
    centered_controls: HTMLElement,
    nr: number,
    i: number,
    anchor_id: number,
    size: number,
) {
    // 0 ~ X, 1 ~ Y
    const orientation = i ? "height" : "width";
    const sizer = document.createElement("div");
    sizer.className = "sizer sizer" + i + " anchor" + anchor_id;

    if (size == dashboard_properties.MAX) {
        sizer.className += " max";
        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        sizer.innerHTML = "max " + orientation;
        sizer.title = "Use maximum available space in this direction";
    } else if (size == dashboard_properties.GROW) {
        sizer.className += " grow";
        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        sizer.innerHTML = "auto " + orientation;
        sizer.title = "Grow in this direction";
    } else {
        sizer.className += " abs";
        sizer.title = "Fixed size (drag border for resize)";
        /* eslint-disable-next-line no-unsanitized/property -- Highlight existing violations CMK-17846 */
        sizer.innerHTML = "manual " + orientation;
        render_resize_controls(centered_controls.parentNode as HTMLElement, i);
    }

    sizer.onclick = () => toggle_sizer(nr, i);

    centered_controls.appendChild(sizer);
}

function render_corner_resizers(controls: HTMLElement) {
    for (let corner_id = 0; corner_id < 4; corner_id++) {
        const resize = document.createElement("div");
        resize.className = "resize resize_corner resize_corner" + corner_id;
        controls.appendChild(resize);
    }
}

function dashlet_toggle_edit(dashlet_obj: HTMLElement, edit?: boolean) {
    const nr = parseInt(dashlet_obj.id.replace("dashlet_", ""));
    const dashlet = dashboard_properties.dashlets[nr];

    edit = edit === undefined ? g_editing : edit;

    let controls: HTMLElement;
    if (edit) {
        // gray out the inner parts of the dashlet
        add_class(dashlet_obj, "edit");

        // Create the dashlet controls
        controls = document.createElement("div");
        controls.setAttribute("id", "dashlet_controls_" + nr);
        controls.className = "controls";
        dashlet_obj.appendChild(controls);
        set_control_size(
            controls,
            dashlet_obj.clientWidth,
            dashlet_obj.clientHeight,
        );

        const d_width = Math.trunc(dashlet_obj.clientWidth);
        const d_height = Math.trunc(dashlet_obj.clientHeight);
        toggle_slim_controls(controls, d_width, d_height);

        const centered_controls = document.createElement("div");
        centered_controls.className = "centered_controls";
        controls.appendChild(centered_controls);

        // IE < 9: Without this fix the controls container is not working
        if (browser.is_ie_below_9()) {
            controls.style.background = "url(about:blank)";
        }

        // Which is the anchor corner?
        const anchor_id = get_anchor_id(dashlet);

        // Create the size / grow indicators and resizer control elements
        if (has_class(dashlet_obj, "resizable")) {
            render_sizer(centered_controls, nr, 0, anchor_id, dashlet.w);
            render_sizer(centered_controls, nr, 1, anchor_id, dashlet.h);

            if (!is_dynamic(dashlet.w) && !is_dynamic(dashlet.h))
                render_corner_resizers(controls);
        }

        const create_a_button = function (
            className: string,
            title: string,
            onclick: () => void,
        ) {
            const element = document.createElement("a");
            element.className = className;
            element.title = title;
            element.onclick = onclick;
            return element;
        };

        // Create the anchors
        for (let i = 0; i < 4; i++) {
            const anchor = create_a_button(
                "anchor anchor" + i,
                "Click to start growing from here",
                () => toggle_anchor(nr, i),
            );
            if (anchor_id == i) {
                anchor.className += " on";
                anchor.title = "Currently growing from here";
                const anchor_image = document.createElement("div");
                anchor_image.className = "anchor_image";
                anchor.appendChild(anchor_image);
                const helper = document.createElement("div");
                add_class(helper, "anchor_label");
                helper.innerHTML = "Anchor";
                anchor.appendChild(helper);
            }
            controls.appendChild(anchor);
        }
        const click_actions = function (target: string) {
            return function () {
                const back_url = makeuri(
                    {},
                    window.location.href,
                    "dashboard.py",
                );
                location.href = makeuri_contextless(
                    {
                        name: dashboard_properties.dashboard_name,
                        id: nr,
                        back: back_url,
                    },
                    target,
                );
            };
        };

        const edits = document.createElement("div");
        edits.className = "editor";
        // Add edit dashlet button
        edits.appendChild(
            create_a_button(
                "edit",
                "Edit properties of this element",
                click_actions("edit_dashlet.py"),
            ),
        );

        // Add clone dashlet button
        edits.appendChild(
            create_a_button(
                "clone",
                "Clone this element",
                click_actions("clone_dashlet.py"),
            ),
        );

        // Add delete dashlet button
        edits.appendChild(
            create_a_button("del", "Delete this element", () =>
                confirm_dialog(
                    {text: "Do you really want to delete this element?"},
                    click_actions("delete_dashlet.py"),
                ),
            ),
        );

        const first_control = centered_controls.firstChild;
        if (first_control) {
            centered_controls.insertBefore(edits, first_control);
        } else {
            centered_controls.appendChild(edits);
        }
    } else {
        // make the inner parts visible again
        remove_class(dashlet_obj, "edit");

        // Remove all dashlet controls
        controls = document.getElementById("dashlet_controls_" + nr)!;
        controls.parentNode!.removeChild(controls);
    }
}

// In case of cycling from ABS to again ABS, restore the previous ABS coords
const g_last_absolute_widths: Record<number, number> = {};
const g_last_absolute_heights: Record<number, number> = {};

function toggle_sizer(nr: number, sizer_id: number) {
    const dashlet = dashboard_properties.dashlets[nr];
    const dashlet_obj = document.getElementById("dashlet_" + nr)!;

    if (sizer_id == 0) {
        if (dashlet.w > 0) {
            g_last_absolute_widths[nr] = dashlet.w;
            dashlet.w = dashboard_properties.GROW;
        } else if (dashlet.w == dashboard_properties.GROW) {
            if (!(nr in g_last_absolute_widths))
                g_last_absolute_widths[nr] =
                    dashlet_obj.clientWidth / dashboard_properties.grid_size;
            dashlet.w = dashboard_properties.MAX;
        } else if (dashlet.w == dashboard_properties.MAX) {
            if (nr in g_last_absolute_widths)
                dashlet.w = g_last_absolute_widths[nr];
            else
                dashlet.w =
                    dashlet_obj.clientWidth / dashboard_properties.grid_size;
        }
    } else {
        if (dashlet.h > 0) {
            g_last_absolute_heights[nr] = dashlet.h;
            dashlet.h = dashboard_properties.GROW;
        } else if (dashlet.h == dashboard_properties.GROW) {
            if (!(nr in g_last_absolute_heights))
                g_last_absolute_heights[nr] =
                    dashlet_obj!.clientHeight / dashboard_properties.grid_size;
            dashlet.h = dashboard_properties.MAX;
        } else if (dashlet.h == dashboard_properties.MAX) {
            if (nr in g_last_absolute_heights)
                dashlet.h = g_last_absolute_heights[nr];
            else
                dashlet.h =
                    dashlet_obj!.clientHeight / dashboard_properties.grid_size;
        }
    }

    bring_dashlet_to_front(dashlet_obj);
    rerender_dashlet_controls(dashlet_obj);
    size_dashlets();
    persist_dashlet_pos(nr);
}

const A_TOP_LEFT = 0;
const A_TOP_RIGHT = 1;
const A_BOTTOM_RIGHT = 2;
const A_BOTTOM_LEFT = 3;

// Calculates the ID of the current dashlet anchor depending
// on the current coordinates
function get_anchor_id(dashlet: Dashlet): number {
    let anchor_id: number;
    if (dashlet.x > 0 && dashlet.y > 0) anchor_id = A_TOP_LEFT;
    else if (dashlet.x <= 0 && dashlet.y > 0) anchor_id = A_TOP_RIGHT;
    else if (dashlet.x <= 0 && dashlet.y <= 0) anchor_id = A_BOTTOM_RIGHT;
    else if (dashlet.x > 0 && dashlet.y <= 0) anchor_id = A_BOTTOM_LEFT;
    return anchor_id!;
}

function toggle_anchor(nr: number, anchor_id: number) {
    if (anchor_id == get_anchor_id(dashboard_properties.dashlets[nr])) return; // anchor has not changed, skip it!

    calculate_relative_dashlet_coords(nr, anchor_id);

    // Visualize the change within the dashlet
    rerender_dashlet_controls(document.getElementById("dashlet_" + nr)!);

    // Apply the change to all rendered dashlets
    size_dashlets();

    persist_dashlet_pos(nr);
}

// We do not want to recompute the dimensions of growing dashlets here,
// use the current effective size
function calculate_relative_dashlet_coords(
    nr: number,
    anchor_id: number | string | undefined = undefined,
) {
    const dashlet = dashboard_properties.dashlets[nr];

    // When the anchor id is not set explicit here autodetect the anchor
    // id which is currently used by the dashlet. Otherwise this function
    // will set a new anchor for the dashlet and recalculate the coordinates
    if (anchor_id === undefined) {
        anchor_id = get_anchor_id(dashlet);
    }

    const dashlet_obj = document.getElementById("dashlet_" + nr)!;

    const x =
        align_to_grid(dashlet_obj!.offsetLeft) / dashboard_properties.grid_size;
    const y =
        align_to_grid(dashlet_obj!.offsetTop) / dashboard_properties.grid_size;
    const w =
        align_to_grid(dashlet_obj!.clientWidth) /
        dashboard_properties.grid_size;
    const h =
        align_to_grid(dashlet_obj!.clientHeight) /
        dashboard_properties.grid_size;

    const screen_size = new Vec(g_dashboard_width, g_dashboard_height);
    const raster_size = screen_size.divide(dashboard_properties.grid_size);

    // Update fixed sizes in coord structure
    if (!is_dynamic(dashlet.w)) dashlet.w = w;
    if (!is_dynamic(dashlet.h)) dashlet.h = h;

    if (anchor_id == A_TOP_LEFT) {
        dashlet.x = x;
        dashlet.y = y;
    } else if (anchor_id == A_TOP_RIGHT) {
        dashlet.x = x + w - (raster_size.x + 2);
        dashlet.y = y;
    } else if (anchor_id == A_BOTTOM_RIGHT) {
        dashlet.x = x + w - (raster_size.x + 2);
        dashlet.y = y + h - (raster_size.y + 2);
    } else if (anchor_id == A_BOTTOM_LEFT) {
        dashlet.x = x;
        dashlet.y = y + h - (raster_size.y + 2);
    }
    dashlet.x += 1;
    dashlet.y += 1;
}

function rerender_dashlet_controls(dashlet_obj: HTMLElement) {
    dashlet_toggle_edit(dashlet_obj, false);
    dashlet_toggle_edit(dashlet_obj, true);
}

/**
 * Dragging of dashlets
 */

let g_dragging: HTMLElement | false = false;
let g_drag_start: GDrag | null = null;

function drag_dashlet_start(event: MouseEvent) {
    if (!g_editing) return true;

    const target = event.target as HTMLElement;
    const button = get_button(event);

    if (
        g_dragging === false &&
        button == "LEFT" &&
        has_class(target, "controls")
    ) {
        g_dragging = target.parentNode as HTMLElement;
        const nr = parseInt(g_dragging.id.replace("dashlet_", ""));
        const dashlet = dashboard_properties.dashlets[nr];

        // minimal dashlet sizes in pixels
        const min_w =
            dashboard_properties.dashlet_min_size[0] *
            dashboard_properties.grid_size;
        const min_h =
            dashboard_properties.dashlet_min_size[1] *
            dashboard_properties.grid_size;

        // reduce the dashlet to the minimum dashlet size for movement bound checks
        let x = g_dragging.offsetLeft;
        let y = g_dragging.offsetTop;
        let w = g_dragging.clientWidth;
        let h = g_dragging.clientHeight;

        const anchor_id = get_anchor_id(dashlet);
        if (anchor_id == A_TOP_LEFT) {
            if (is_dynamic(dashlet.w)) w = min_w;
            if (is_dynamic(dashlet.h)) h = min_h;
        } else if (anchor_id == A_TOP_RIGHT) {
            if (is_dynamic(dashlet.w)) {
                x = x + w - min_w;
                w = min_w;
            }
            if (is_dynamic(dashlet.h)) h = min_h;
        } else if (anchor_id == A_BOTTOM_RIGHT) {
            if (is_dynamic(dashlet.w)) {
                x = x + w - min_w;
                w = min_w;
            }
            if (is_dynamic(dashlet.h)) {
                y = y + h - min_h;
                h = min_h;
            }
        } else if (anchor_id == A_BOTTOM_LEFT) {
            if (is_dynamic(dashlet.w)) w = min_w;
            if (is_dynamic(dashlet.h)) {
                y = y + h - min_h;
                h = min_h;
            }
        }

        g_drag_start = {
            // mouse position in px relative to dashboard
            m_x: event.clientX - g_dashboard_left!,
            m_y: event.clientY - g_dashboard_top!,
            // x/y position of shrunk dashlet in px relative to dashboard
            x: x,
            y: y,
            // size of shrunk dashlet in px
            w: w,
            h: h,
        } as GDrag;

        bring_dashlet_to_front(g_dragging);

        prevent_default_events(event);
        return false;
    }
    return true;
}

function drag_dashlet(event: MouseEvent): true | void {
    // mosue coords in px relative to dashboard
    const mouse_x = event.clientX - g_dashboard_left!;
    const mouse_y = event.clientY - g_dashboard_top!;

    if (!g_dragging) return true;
    const g_drag_start_const: GDrag = g_drag_start!;

    const nr = parseInt(g_dragging.id.replace("dashlet_", ""));
    let dashlet_obj = g_dragging;
    // get the relative mouse position offset to the dragging beginning
    const diff_x = align_to_grid(g_drag_start_const.m_x - mouse_x);
    const diff_y = align_to_grid(g_drag_start_const.m_y - mouse_y);

    const x = g_drag_start_const.x - diff_x;
    const y = g_drag_start_const.y - diff_y;
    const w = g_drag_start_const.w;
    const h = g_drag_start_const.h;

    const board_w = align_to_grid(g_dashboard_width!);
    const board_h = align_to_grid(g_dashboard_height!);
    dashlet_obj = dashlet_obj as HTMLElement;
    if (x < 0) {
        // reached left limit: left screen border
        dashlet_obj.style.left = "0px";
        dashlet_obj.style.width = w + "px";
    } else if (x + w > board_w) {
        // reached right limit: right screen border
        dashlet_obj.style.left = board_w - w + "px";
        dashlet_obj.style.width = w + "px";
    } else {
        dashlet_obj.style.left = x + "px";
        dashlet_obj.style.width = w + "px";
    }

    if (y < 0) {
        // reached top limit: top screen border
        dashlet_obj.style.top = "0px";
        dashlet_obj.style.height = h + "px";
    } else if (y + h > board_h) {
        // reached bottom limit: bottom screen border
        dashlet_obj.style.top = board_h - h + "px";
        dashlet_obj.style.height = h + "px";
    } else {
        dashlet_obj.style.top = y + "px";
        dashlet_obj.style.height = h + "px";
    }
    // Calculates new data for the internal coord structure
    calculate_relative_dashlet_coords(nr);

    // Redo dynamic sizing and rendering
    size_dashlets();
}

function drag_dashlet_stop(_event: Event) {
    if (!g_dragging) return true;

    const nr = parseInt(g_dragging.id.replace("dashlet_", ""));
    g_dragging = false;
    g_drag_start = null;

    persist_dashlet_pos(nr);
    return false;
}

function persist_dashlet_pos(nr: number) {
    const dashlet = dashboard_properties.dashlets[nr];

    if (
        !Number.isInteger(dashlet.x) ||
        !Number.isInteger(dashlet.y) ||
        !Number.isInteger(dashlet.w) ||
        !Number.isInteger(dashlet.h)
    ) {
        console.error(
            "Error: Invalid element coordinates found. Please report " +
                "this issue (" +
                JSON.stringify(dashlet) +
                ").",
        );
        return;
    }

    call_ajax(
        "ajax_dashlet_pos.py?name=" +
            dashboard_properties.dashboard_name +
            "&id=" +
            nr +
            "&x=" +
            dashboard_properties.dashlets[nr].x +
            "&y=" +
            dashboard_properties.dashlets[nr].y +
            "&w=" +
            dashboard_properties.dashlets[nr].w +
            "&h=" +
            dashboard_properties.dashlets[nr].h,
        {
            response_handler: handle_dashlet_post_response,
            handler_data: null,
            error_handler: undefined,
            add_ajax_id: false,
        },
    );
}

function handle_dashlet_post_response(_unused: any, response_text: string) {
    const parts = response_text.split(" ");
    if (parts[0] != "OK") {
        console.error("Error: " + response_text);
    } else {
        dashboard_properties.dashboard_mtime = parseInt(parts[1]);
    }
}

function bring_dashlet_to_front(obj: HTMLElement) {
    document.querySelectorAll("div.dashlet").forEach(function (elem) {
        (elem as HTMLElement).style.zIndex = "1";
    });
    obj.style.zIndex = "80";
}

/**
 * Resizing of dashlets
 */

// false or the resizer dom object currently being worked with
let g_resizing: false | HTMLElement = false;
let g_resize_start: GDrag | null = null;

function resize_dashlet_start(event: MouseEvent) {
    if (!g_editing) return true;

    const target = event.target as HTMLElement;
    const button = get_button(event);

    if (
        g_resizing === false &&
        button == "LEFT" &&
        has_class(target, "resize")
    ) {
        const dashlet_obj = target.parentNode!.parentNode as HTMLElement;

        g_resizing = target;
        g_resize_start = {
            // mouse position in px
            m_x: event.clientX,
            m_y: event.clientY,
            // initial position in px
            x: dashlet_obj.offsetLeft,
            y: dashlet_obj.offsetTop,
            // initial size in px
            w: dashlet_obj.clientWidth,
            h: dashlet_obj.clientHeight,
        };

        bring_dashlet_to_front(dashlet_obj);

        prevent_default_events(event);
        return false;
    }
    return true;
}

function get_horizontal_direction(
    resizer: HTMLElement,
): "left" | "right" | void {
    if (
        has_class(resizer, "resize0_0") ||
        has_class(resizer, "resize_corner0") ||
        has_class(resizer, "resize_corner3")
    )
        return "left";
    else if (
        has_class(resizer, "resize0_1") ||
        has_class(resizer, "resize_corner1") ||
        has_class(resizer, "resize_corner2")
    )
        return "right";
}

function get_vertical_direction(resizer: HTMLElement): "top" | "bottom" | void {
    if (
        has_class(resizer, "resize1_0") ||
        has_class(resizer, "resize_corner0") ||
        has_class(resizer, "resize_corner1")
    )
        return "top";
    else if (
        has_class(resizer, "resize1_1") ||
        has_class(resizer, "resize_corner2") ||
        has_class(resizer, "resize_corner3")
    )
        return "bottom";
}

function resize_dashlet(event: MouseEvent): true | void {
    if (!g_resizing) return true;

    const dashlet_obj = (g_resizing as HTMLElement).parentNode!
        .parentNode as HTMLElement;
    const nr = parseInt(dashlet_obj.id.replace("dashlet_", ""));
    if (!g_resize_start) throw new Error("g_resize_start is not defined!");
    let diff_x = align_to_grid(Math.abs(g_resize_start.m_x - event.clientX));
    let diff_y = align_to_grid(Math.abs(g_resize_start.m_y - event.clientY));

    if (event.clientX > g_resize_start.m_x) diff_x *= -1;
    if (event.clientY > g_resize_start.m_y) diff_y *= -1;

    const board_w = align_to_grid(g_dashboard_width!);
    const board_h = align_to_grid(g_dashboard_height!);

    const min_w =
        dashboard_properties.dashlet_min_size[0] *
        dashboard_properties.grid_size;
    const min_h =
        dashboard_properties.dashlet_min_size[1] *
        dashboard_properties.grid_size;

    if (get_horizontal_direction(g_resizing) == "left") {
        // resizing with left border
        const new_x = g_resize_start.x - diff_x;
        if (new_x < 0) {
            // reached left limit: left screen border
            dashlet_obj.style.left = "0px";
            dashlet_obj.style.width =
                g_resize_start.w + g_resize_start.x + "px";
        } else if (g_resize_start.w + diff_x < min_w) {
            // reached right limit: minimum dashlet width
            dashlet_obj.style.width = min_w + "px";
        } else {
            // normal resize step
            dashlet_obj.style.left = new_x + "px";
            dashlet_obj.style.width = g_resize_start.w + diff_x + "px";
        }
    } else if (get_horizontal_direction(g_resizing) == "right") {
        // resizing with right border
        if (g_resize_start.x + g_resize_start.w - diff_x > board_w) {
            // reached right limit: right screen border
            dashlet_obj.style.width = board_w - g_resize_start.x + "px";
        } else if (g_resize_start.w - diff_x < min_w) {
            // reached left limit: minimum dashlet width
            dashlet_obj.style.width = min_w + "px";
        } else {
            // normal resize step
            dashlet_obj.style.width = g_resize_start.w - diff_x + "px";
        }
    }

    if (get_vertical_direction(g_resizing) == "top") {
        // resizing with top border
        const new_y = g_resize_start.y - diff_y;
        if (new_y < 0) {
            // reached top limit: top screen border
            dashlet_obj.style.top = "0px";
            dashlet_obj.style.height =
                g_resize_start.h + g_resize_start.y + "px";
        } else if (g_resize_start.h + diff_y < min_h) {
            // reached bottom limit: minimum dashlet height
            dashlet_obj.style.height = min_h + "px";
        } else {
            // normal resize step
            dashlet_obj.style.top = new_y + "px";
            dashlet_obj.style.height = g_resize_start.h + diff_y + "px";
        }
    } else if (get_vertical_direction(g_resizing) == "bottom") {
        // resizing with bottom border
        if (g_resize_start.y + g_resize_start.h - diff_y >= board_h) {
            // reached bottom limit: bottom screen border
            dashlet_obj.style.height = board_h - g_resize_start.y + "px";
        } else if (g_resize_start.h - diff_y < min_h) {
            // reached top limit: minimum dashlet height
            dashlet_obj.style.height = min_h + "px";
        } else {
            // normal resize step
            dashlet_obj.style.height = g_resize_start.h - diff_y + "px";
        }
    }
    const new_width = Math.trunc(dashlet_obj.clientWidth);
    const new_height = Math.trunc(dashlet_obj.clientHeight);
    toggle_slim_controls(
        document.getElementById("dashlet_controls_" + nr)!,
        new_width,
        new_height,
    );

    // Calculates new data for the internal coord structure
    calculate_relative_dashlet_coords(nr);

    // Redo dynamic sizing and rendering
    size_dashlets();
}

function resize_dashlet_stop(_event: Event) {
    if (!g_resizing) return true;

    const dashlet_obj = (g_resizing as HTMLElement).parentNode
        ?.parentNode as HTMLElement;
    const nr = parseInt(dashlet_obj.id.replace("dashlet_", ""));
    g_resizing = false;

    dashlet_resized(nr, dashlet_obj);
    persist_dashlet_pos(nr);
    return false;
}

function dashlet_resized(nr: number, dashlet_obj: HTMLElement) {
    if (typeof reload_on_resize[nr] != "undefined") {
        const base_url = reload_on_resize[nr];
        const iframe = document.getElementById(
            "dashlet_iframe_" + nr,
        ) as HTMLFrameElement;
        iframe.src =
            base_url +
            "&width=" +
            dashlet_obj.clientWidth +
            "&height=" +
            dashlet_obj.clientHeight;
    }
    const on_resize: undefined | (() => void) | string =
        dashboard_properties.on_resize_dashlets[nr];

    if (typeof on_resize !== "undefined" && typeof on_resize !== "string") {
        on_resize();
    }
}

export function has_canvas_support() {
    return document.createElement("canvas").getContext;
}

/*
 * Register the global event handlers, used for dragging of dashlets,
 * dialog control and resizing of dashlets
 */
export function register_event_handlers() {
    add_event_handler("mousemove", function (e) {
        return drag_dashlet(e as MouseEvent) && resize_dashlet(e as MouseEvent);
    });
    add_event_handler("mousedown", function (e) {
        return (
            drag_dashlet_start(e as MouseEvent) &&
            resize_dashlet_start(e as MouseEvent)
        );
    });
    add_event_handler("mouseup", function (e) {
        return drag_dashlet_stop(e) && resize_dashlet_stop(e as MouseEvent);
    });

    // Totally disable the context menu for all dashboards
    add_event_handler("contextmenu", function (e) {
        prevent_default_events(e);
        return false;
    });

    // Stop dashlet drag and resize whenever the mouse leaves the content area
    add_event_handler(
        "mouseleave",
        function (e) {
            return drag_dashlet_stop(e) && resize_dashlet_stop(e);
        },
        document,
    );
}

export function chart_pie(
    pie_id: string,
    x_scale: number,
    radius: number,
    color: string | CanvasGradient | CanvasPattern,
    right_side: boolean,
    pie_diameter: number,
) {
    let context = (
        document.getElementById(pie_id + "_stats") as HTMLCanvasElement
    ).getContext("2d");
    if (!context) return;
    const pie_x = pie_diameter / 2;
    const pie_y = pie_diameter / 2;
    const pie_d = pie_diameter;
    context.fillStyle = color;
    context.save();
    context.translate(pie_x, pie_y);
    context.scale(x_scale, 1);
    context.beginPath();
    if (right_side)
        context.arc(
            0,
            0,
            (pie_d / 2) * radius,
            1.5 * Math.PI,
            0.5 * Math.PI,
            false,
        );
    else
        context.arc(
            0,
            0,
            (pie_d / 2) * radius,
            0.5 * Math.PI,
            1.5 * Math.PI,
            false,
        );
    context.closePath();
    context.fill();
    context.restore();
    context = null;
}

function toggle_slim_controls(
    controls_obj: HTMLElement,
    width: number,
    height: number,
) {
    const thresholds = {} as Thresholds;
    for (const key in dashboard_properties.slim_editor_thresholds) {
        //@ts-ignore
        thresholds[key] =
            //@ts-ignore
            dashboard_properties.slim_editor_thresholds[key] *
            dashboard_properties.grid_size;
    }

    if (width < thresholds.width || height < thresholds.height) {
        add_class(controls_obj, "slim_controls");
    } else {
        remove_class(controls_obj, "slim_controls");
    }
}
