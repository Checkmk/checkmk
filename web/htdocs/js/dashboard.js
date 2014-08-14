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

// dashlet ids and urls
var reload_on_resize = {};

function size_dashlets() {
    var size_info = calculate_dashlets();
    var oDash = null;
    for (var d_number = 0; d_number < size_info.length; d_number++) {
        var dashlet = size_info[d_number];
        var d_left    = dashlet[0];
        var d_top     = dashlet[1];
        var d_width   = dashlet[2];
        var d_height  = dashlet[3];
        var disstyle = "block";

        // check if dashlet has title and resize its width
        oDash = document.getElementById("dashlet_title_" + d_number);
        var has_title = false;
        if (oDash) {
            has_title = true;
            //if browser window to small prevent js error
            if(d_width <= 20){
                d_width = 21;
            }
            // 14 => 9 title padding + empty space on right of dashlet
            oDash.style.width  = (d_width - 14) + "px";
            oDash.style.display = disstyle;
        }

        // resize outer div
        oDash = document.getElementById("dashlet_" + d_number);
        if(oDash) {
            oDash.style.display  = disstyle;
            oDash.style.left     = d_left + "px";
            oDash.style.top      = d_top + "px";
            oDash.style.width    = d_width + "px";
            oDash.style.height   = d_height + "px";
        }

        var top_padding = dashlet_padding[0];
        if (!has_title)
            top_padding = dashlet_padding[4];

        var netto_height = d_height - top_padding - dashlet_padding[2];
        var netto_width  = d_width  - dashlet_padding[1] - dashlet_padding[3];

        // resize content div
        oDash = document.getElementById("dashlet_inner_" + d_number);
        if(oDash) {
            oDash.style.display  = disstyle;

            var old_width  = oDash.clientWidth;
            var old_height = oDash.clientHeight;

            oDash.style.left   = dashlet_padding[3] + "px";
            oDash.style.top    = top_padding + "px";
            if (netto_width > 0)
                oDash.style.width  = netto_width + "px";
            if (netto_height > 0)
                oDash.style.height = netto_height + "px";

            if (old_width != oDash.clientWidth || old_height != oDash.clientHeight) {
                if (!g_resizing
                    || parseInt(g_resizing.parentNode.parentNode.id.replace('dashlet_', '')) != d_number)
                dashlet_resized(d_number, oDash);
            }
        }
    }
    oDash = null;
}

function vec(x, y) {
    this.x = x || 0;
    this.y = y || 0;
}

vec.prototype = {
    divide: function(v) {
        return new vec(~~(this.x / v.x), ~~(this.y / v.y));
    },
    add: function(v) {
        return new vec(this.x + v.x, this.y + v.y);
    },
    make_absolute: function(size_v) {
        return new vec(this.x < 0 ? this.x + size_v.x + 1 : this.x - 1,
                       this.y < 0 ? this.y + size_v.y + 1 : this.y - 1);
    },
    // Compute the initial size of the dashlet. If MAX is used,
    // then the dashlet consumes all space in its growing direction,
    // regardless of any other dashlets.
    initial_size: function(pos_v, grid_v) {
        return new vec(
            (this.x == MAX ? grid_v.x - Math.abs(pos_v.x) + 1 : (this.x == GROW ? dashlet_min_size[0] : this.x)),
            (this.y == MAX ? grid_v.y - Math.abs(pos_v.y) + 1 : (this.y == GROW ? dashlet_min_size[1] : this.y))
        );
    },
    // return codes:
    //  0: absolute size, no growth
    //  1: grow direction right, down
    // -1: grow direction left, up
    compute_grow_by: function(size_v) {
        return new vec(
            (size_v.x != GROW ? 0 : (this.x < 0 ? -1 : 1)),
            (size_v.y != GROW ? 0 : (this.y < 0 ? -1 : 1))
        );
    },
    toString: function() {
        return this.x+'/'+this.y;
    }
};

function calculate_dashlets() {
    var screen_size = new vec(g_dashboard_width, g_dashboard_height);
    var raster_size = screen_size.divide(grid_size);
    var used_matrix = {};
    var positions   = [];

    // first place all dashlets at their absolute positions
    for (var nr = 0; nr < dashlets.length; nr++) {
        var dashlet = dashlets[nr];

        // Relative position is as noted in the declaration. 1,1 => top left origin,
        // -1,-1 => bottom right origin, 0 is not allowed here
        // starting from 1, negative means: from right/bottom
        var rel_position = new vec(dashlet.x, dashlet.y);

        // Compute the absolute position, this time from 0 to raster_size-1
        var abs_position = rel_position.make_absolute(raster_size);

        // The size in raster-elements. A 0 for a dimension means growth. No negative values here.
        var size = new vec(dashlet.w, dashlet.h);

        // Compute the minimum used size for the dashlet. For growth-dimensions we start with 1
        var used_size = size.initial_size(rel_position, raster_size);

        // Now compute the rectangle that is currently occupied. The choords
        // of bottomright are *not* included.
        var top, left, right, bottom;
        if (rel_position.x > 0) {
            left = abs_position.x;
            right = left + used_size.x;
        }
        else {
            right = abs_position.x;
            left = right - used_size.x;
        }

        if (rel_position.y > 0) {
            top = abs_position.y
            bottom = top + used_size.y
        }
        else {
            bottom = abs_position.y;
            top = bottom - used_size.y;
        }

        // Allocate used squares in matrix. If not all squares we need are free,
        // then the dashboard is too small for all dashlets (as it seems).
        for (var x = left; x < right; x++) {
            for (var y = top; y < bottom; y++) {
                used_matrix[x+' '+y] = true;
            }
        }
        // Helper variable for how to grow, both x and y in [-1, 0, 1]
        var grow_by = rel_position.compute_grow_by(size);

        positions.push([left, top, right, bottom, grow_by]);
    }

    var try_allocate = function(left, top, right, bottom) {
        // Try if all needed squares are free
        for (var x = left; x < right; x++)
            for (var y = top; y < bottom; y++)
                if (x+' '+y in used_matrix)
                    return false;

        // Allocate all needed squares
        for (var x = left; x < right; x++)
            for (var y = top; y < bottom; y++)
                used_matrix[x+' '+y] = true;

        return true;
    };

    // Now try to expand all elastic rectangles as far as possible
    // FIXME: Das hier muesste man optimieren
    var at_least_one_expanded = true;
    while (at_least_one_expanded) {
        at_least_one_expanded = false;
        var new_positions = []
        for (var nr = 0; nr < positions.length; nr++) {
            var left    = positions[nr][0],
                top     = positions[nr][1],
                right   = positions[nr][2],
                bottom  = positions[nr][3],
                grow_by = positions[nr][4];

            // try to grow in X direction by one
            if (grow_by.x > 0 && right < raster_size.x && try_allocate(right, top, right+1, bottom)) {
                at_least_one_expanded = true;
                right += 1;
            }
            else if (grow_by.x < 0 && left > 0 && try_allocate(left-1, top, left, bottom)) {
                at_least_one_expanded = true;
                left -= 1;
            }

            // try to grow in Y direction by one
            if (grow_by.y > 0 && bottom < raster_size.y && try_allocate(left, bottom, right, bottom+1)) {
                at_least_one_expanded = true;
                bottom += 1;
            }
            else if (grow_by.y < 0 && top > 0 && try_allocate(left, top-1, right, top)) {
                at_least_one_expanded = true;
                top -= 1;
            }
            new_positions.push([left, top, right, bottom, grow_by]);
        }
        positions = new_positions;
    }

    var size_info = [];
    for (var nr = 0; nr < positions.length; nr++) {
        var left    = positions[nr][0],
            top     = positions[nr][1],
            right   = positions[nr][2],
            bottom  = positions[nr][3];
        size_info.push([
            left * grid_size.x,
            top * grid_size.y,
            (right - left) * grid_size.x,
            (bottom - top) * grid_size.y
        ]);
    }
    return size_info;
}

var g_dashboard_resizer = null;
var g_dashboard_top     = null
var g_dashboard_left    = null
var g_dashboard_width   = null;
var g_dashboard_height  = null;

function calculate_dashboard() {
    if (g_dashboard_resizer !== null)
        return; // another resize is processed
    g_dashboard_resizer = true;

    g_dashboard_top    = header_height + screen_margin;
    g_dashboard_left   = screen_margin;
    g_dashboard_width  = pageWidth() - 2*screen_margin;
    g_dashboard_height = pageHeight() - 2*screen_margin - header_height;

    var oDash = document.getElementById("dashboard");
    oDash.style.left     = g_dashboard_left + "px";
    oDash.style.top      = g_dashboard_top + "px";
    oDash.style.width    = g_dashboard_width + "px";
    oDash.style.height   = g_dashboard_height + "px";

    size_dashlets();
    g_dashboard_resizer = null;
}

function dashboard_scheduler(initial) {
    var timestamp = Date.parse(new Date()) / 1000;
    var newcontent = "";
    for(var i = 0; i < refresh_dashlets.length; i++) {
        var nr      = refresh_dashlets[i][0];
        var refresh = refresh_dashlets[i][1];
        var url     = refresh_dashlets[i][2];

        if ((initial && document.getElementById("dashlet_inner_" + nr).innerHTML == '')
                || (refresh > 0 && timestamp % refresh == 0)) {
            get_url(url + "&mtime=" + dashboard_mtime, dashboard_update_contents, "dashlet_inner_" + nr);
        }
    }

    // Update timestamp every minute
    // Required if there are no refresh_dashlets present or all refresh times are > 60sec
    if (timestamp % 60 == 0) {
        updateHeaderTime();
    }

    setTimeout(function() { dashboard_scheduler(0); }, 1000);
}

function dashboard_update_contents(id, response_text) {
    // Update the header time
    updateHeaderTime();

    // Call the generic function to replace the dashlet inner code
    updateContents(id, response_text);
}

function update_dashlet(id, code) {
  var obj = document.getElementById(id);
  if (obj) {
    obj.innerHTML = code;
    executeJS(id);
    obj = null;
  }
}

//
// DASHBOARD EDITING
//

function toggle_dashboard_controls(show, event) {
    var controls = document.getElementById('controls');
    if (!controls)
        return; // maybe not permitted -> skip

    if (typeof show === 'undefined')
        var show = controls.style.display == 'none';

    if (show) {
        controls.style.display = 'block';
        hide_submenus();

        // Gather and update the position of the menu
        if (event) {
            var target = getTarget(event);
            controls.style.left = (event.clientX - target.offsetLeft + 5) + 'px';
            controls.style.top  = (event.clientY - target.offsetTop + 5) + 'px';

            var dashboard = document.getElementById('dashboard');

            // When menu is out of screen on the right, move to left
            if (controls.offsetLeft + controls.clientWidth > dashboard.clientWidth)
                controls.style.left = (controls.offsetLeft - controls.clientWidth - 15) + 'px';

            // When menu is out of screen on the bottom, move to top
            if (controls.offsetTop + controls.clientHeight > dashboard.clientHeight) {
                var new_top = controls.offsetTop - controls.clientHeight - 5;
                if (target != dashboard)
                    new_top -= dashboard.offsetTop;

                controls.style.top = new_top + 'px';
            }
        }
    }
    else {
        controls.style.display = 'none';
    }
}

function hide_submenus() {
    // hide all submenus
    var subs = document.getElementsByClassName('sub');
    for (var i = 0; i < subs.length; i++)
        subs[i].style.display = 'none';
}

function show_submenu(id) {
    document.getElementById(id + '_sub').style.display = 'block';
}

var g_editing = false;

function toggle_dashboard_edit() {
    // First hide the controls menu
    toggle_dashboard_controls(false);

    g_editing = !g_editing;

    document.getElementById('control_edit').style.display = !g_editing ? 'block' : 'none';
    document.getElementById('control_add').style.display = g_editing ? 'block' : 'none';
    document.getElementById('control_view').style.display = g_editing ? 'block' : 'none';

    var dashlet_divs = document.getElementsByClassName('dashlet');
    for (var i = 0; i < dashlet_divs.length; i++)
        dashlet_toggle_edit(dashlet_divs[i]);

    toggle_grid();
}

function toggle_grid() {
    if (!g_editing) {
        remove_class(document.getElementById('dashboard'), 'grid');
    } else {
        add_class(document.getElementById('dashboard'), 'grid');
    }
}

function active_anchor(coords) {
    var active = 0;
    if (coords.x < 0 && coords.y >= 0)
        active = 1;
    else if (coords.x < 0 && coords.y < 0)
        active = 2;
    else if (coords.x >= 0 && coords.y < 0)
        active = 3;
    return active
}

// The resize controls are transparent areas at the border of the
// snapin which give the user the option to dragresize the dashlets
// in the dimension where absolute sizes are to be used.
//
// render top/bottom or left/right areas depending on dimension i
function render_resize_controls(controls, i, active) {
    for (var a = 0; a < 2; a++) {
        var resize = document.createElement('div');
        resize.className = 'resize resize'+i+' resize'+i+'_'+a;
        controls.appendChild(resize);
    }
}

function render_sizer(controls, id, i, active, size) {
    // 0 ~ X, 1 ~ Y
    var sizer = document.createElement('div');
    sizer.className = 'sizer sizer'+i+' anchor'+active;

    // create the sizer label
    var sizer_lbl = document.createElement('div');
    sizer_lbl.className = 'sizer_lbl sizer_lbl'+i+' anchor'+active;

    if (size == MAX) {
        sizer.className += ' max';
        sizer_lbl.innerHTML = 'MAX';
    }
    else if (size == GROW) {
        sizer.className += ' grow';
        sizer_lbl.innerHTML = 'GROW';
    }
    else {
        sizer.className += ' abs';
        render_resize_controls(controls, i, active);
    }

    // js magic stuff - closures!
    sizer.onclick = function(dashlet_id, sizer_id) {
        return function() {
            toggle_sizer(dashlet_id, sizer_id);
        };
    }(id, i);
    sizer_lbl.onclick = sizer.onclick;

    controls.appendChild(sizer);
    if (size == MAX || size == GROW)
        controls.appendChild(sizer_lbl);
}

function dashlet_toggle_edit(dashlet, edit) {
    var id = parseInt(dashlet.id.replace('dashlet_', ''));
    var inner = document.getElementById('dashlet_inner_'+id);
    var coords = dashlets[id];

    var edit = edit === undefined ? g_editing : edit;

    if (edit) {
        // gray out the inner parts of the dashlet
        add_class(dashlet, 'edit');

        // Create the dashlet controls
        var controls = document.createElement('div');
        controls.setAttribute('id', 'dashlet_controls_'+id);
        controls.className = 'controls';
        dashlet.appendChild(controls);

        // IE < 9: Without this fix the controls container is not working
        if (is_ie_below_9()) {
            controls.style.background = 'url(about:blank)';
        }

        // Which is the anchor corner?
        // 0: topleft, 1: topright, 2: bottomright, 3: bottomleft
        var active = active_anchor(coords);

        // Create the size / grow indicators
        if (has_class(dashlet, 'resizable')) {
            for (var i = 0; i < 2; i ++) {
                if (i == 0)
                    render_sizer(controls, id, i, active, coords.w);
                else
                    render_sizer(controls, id, i, active, coords.h);
            }
        }

        // Create the anchors
        for (var i = 0; i < 4; i++) {
            var anchor = document.createElement('a');
            anchor.className = 'anchor anchor'+i;
            if (active != i)
                anchor.className += ' off';

            // js magic stuff - closures!
            anchor.onclick = function(dashlet_id, anchor_id) {
                return function() {
                    toggle_anchor(dashlet_id, anchor_id);
                };
            }(id, i);

            controls.appendChild(anchor);
        }

        // Add edit dashlet button
        var edit = document.createElement('a');
        edit.className = 'edit';
        edit.onclick = function(dashlet_id, board_name) {
            return function() {
                location.href = 'edit_dashlet.py?name=' + board_name + '&id=' + dashlet_id
                                + '&back=' + encodeURIComponent(dashboard_url);
            };
        }(id, dashboard_name);
        controls.appendChild(edit);

        // Add delete dashlet button
        var del = document.createElement('a');
        del.className = 'del';
        del.onclick = function(dashlet_id, board_name) {
            return function() {
                location.href = 'delete_dashlet.py?name=' + board_name + '&id=' + dashlet_id
                                + '&back=' + encodeURIComponent(dashboard_url);
            };
        }(id, dashboard_name);
        controls.appendChild(del);

    } else {
        // make the inner parts visible again
        remove_class(dashlet, 'edit');

        // Remove all dashlet controls
        var controls = document.getElementById('dashlet_controls_'+id);
        controls.parentNode.removeChild(controls);
    }
}

// In case of cycling from ABS to again ABS, restore the previous ABS coords
var g_last_absolute_widths  = {};
var g_last_absolute_heights = {};

function toggle_sizer(nr, sizer_id) {
    var dashlet = dashlets[nr];
    var dashlet_obj = document.getElementById('dashlet_'+nr);

    if (sizer_id == 0) {
        if (dashlet.w > 0) {
            g_last_absolute_widths[nr] = dashlet.w;
            dashlet.w = GROW;
        }
        else if (dashlet.w == GROW) {
            dashlet.w = MAX;
        }
        else if (dashlet.w == MAX) {
            if (nr in g_last_absolute_widths)
                dashlet.w = g_last_absolute_widths[nr];
            else
                dashlet.w = dashlet_obj.clientWidth / grid_size.x;
        }
    }
    else {
        if (dashlet.h > 0) {
            g_last_absolute_heights[nr] = dashlet.h;
            dashlet.h = GROW;
        }
        else if (dashlet.h == GROW) {
            dashlet.h = MAX;
        }
        else if (dashlet.h == MAX) {
            if (nr in g_last_absolute_heights)
                dashlet.h = g_last_absolute_heights[nr];
            else
                dashlet.h = dashlet_obj.clientHeight / grid_size.y;
        }
    }

    rerender_dashlet_controls(dashlet_obj);
    size_dashlets();
    persist_dashlet_pos(nr);
}

function toggle_anchor(nr, anchor_id) {
    var dashlet = dashlets[nr];
    if (anchor_id == 0 && dashlet.x > 0 && dashlet.y > 0
        || anchor_id == 1 && dashlet.x <= 0 && dashlet.y > 0
        || anchor_id == 2 && dashlet.x <= 0 && dashlet.y <= 0
        || anchor_id == 3 && dashlet.x > 0 && dashlet.y <= 0)
        return; // anchor has not changed, skip it!

    compute_dashlet_coords(nr, anchor_id);

    // Visualize the change within the dashlet
    rerender_dashlet_controls(document.getElementById('dashlet_'+nr));

    // Apply the change to all rendered dashlets
    size_dashlets();

    persist_dashlet_pos(nr);
}

// We do not want to recompute the dimensions of growing dashlets here,
// use the current effective size
function compute_dashlet_coords(nr, anchor_id, topleft_pos) {
    var dashlet = dashlets[nr];

    // When the anchor id is not set explicit here autodetect the anchor
    // id which is currently used by the dashlet
    if (anchor_id === null) {
        var anchor_id;
        if (dashlet.x > 0 && dashlet.y > 0)
            anchor_id = 0;
        else if (dashlet.x <= 0 && dashlet.y > 0)
            anchor_id = 1;
        else if (dashlet.x <= 0 && dashlet.y <= 0)
            anchor_id = 2;
        else if (dashlet.x > 0 && dashlet.y <= 0)
            anchor_id = 3;
    }

    var dashlet_obj = document.getElementById('dashlet_' + nr);
    var width  = dashlet_obj.clientWidth / grid_size.x;
    var height = dashlet_obj.clientHeight / grid_size.y;
    var size         = new vec(width, height);
    var screen_size  = new vec(g_dashboard_width, g_dashboard_height);
    var raster_size  = screen_size.divide(grid_size);

    if (topleft_pos === undefined) {
        var rel_position = new vec(dashlet.x, dashlet.y);
        var abs_position = rel_position.make_absolute(raster_size);
        var topleft_pos  = new vec(rel_position.x > 0 ? abs_position.x : abs_position.x - size.x,
                                   rel_position.y > 0 ? abs_position.y : abs_position.y - size.y);
    }

    if (anchor_id == 0) {
        dashlet.x = topleft_pos.x;
        dashlet.y = topleft_pos.y;
    }
    else if (anchor_id == 1) {
        dashlet.x = (topleft_pos.x + size.x) - (raster_size.x + 2);
        dashlet.y = topleft_pos.y
    }
    else if (anchor_id == 2) {
        dashlet.x = (topleft_pos.x + size.x) - (raster_size.x + 2);
        dashlet.y = (topleft_pos.y + size.y) - (raster_size.y + 2);
    }
    else if (anchor_id == 3) {
        dashlet.x = topleft_pos.x;
        dashlet.y = (topleft_pos.y + size.y) - (raster_size.y + 2);
    }
    dashlet.x += 1;
    dashlet.y += 1;
}

function rerender_dashlet_controls(dashlet_obj) {
    dashlet_toggle_edit(dashlet_obj, false);
    dashlet_toggle_edit(dashlet_obj, true);
}

// Handle misc events when in editing mode and clicks have made on general elements
function body_click_handler(event) {
    if (!event)
        event = window.event;

    var target = getTarget(event);
    var button = getButton(event);

    if (g_editing && target.id == 'dashboard' && button == 'RIGHT') {
        // right click on the empty dashboard area
        toggle_dashboard_controls(undefined, event);
        prevent_default_events(event);
        return false;
    }
    else if (target.parentNode.id == 'controls_toggle' && button == 'LEFT') {
        // left click on the controls menu
        toggle_dashboard_controls(undefined, event);
        prevent_default_events(event);
        return false;
    }
    else if (target.parentNode.id != 'controls_toggle'
             && (!target.parentNode.parentNode || !has_class(target.parentNode.parentNode, 'menu'))) {
        // Hide the controls menu when clicked somewhere else
        toggle_dashboard_controls(false);
    }

    return true;
}
/**
 * Dragging of dashlets
 */

var g_dragging = false;
var g_orig_pos = null;
var g_mouse_offset = null;

function drag_dashlet_start(event) {
    if (!event)
        event = window.event;

    if (!g_editing)
        return true;

    var target = getTarget(event);
    var button = getButton(event);

    if (g_dragging === false && button == 'LEFT' && has_class(target, 'controls')) {
        g_dragging = target.parentNode;
        g_orig_pos = [ target.parentNode.offsetLeft, target.parentNode.offsetTop ];
        g_mouse_offset = [
            event.clientX - target.parentNode.offsetLeft,
            event.clientY - target.parentNode.offsetTop
        ];

        edit_visualize(g_dragging, true);

        prevent_default_events(event);
        return false;
    }
    return true;
}

function drag_dashlet(event) {
    if (!event)
        event = window.event;

    if (!g_dragging)
        return true;

    // position of the dashlet in x/y browser coordinates, rounded to grid size
    var x = ~~((event.clientX - g_mouse_offset[0]) / grid_size.x) * grid_size.x;
    var y = ~~((event.clientY - g_mouse_offset[1]) / grid_size.y) * grid_size.y;

    var nr = parseInt(g_dragging.id.replace('dashlet_', ''));
    if (dashlets[nr].x == x / grid_size.x + 1 && dashlets[nr].y == y / grid_size.y + 1) {
        return; // skip non movement!
    }

    // Prevent dragging out of screen
    if (x < 0)
        x = 0;
    if (y < 0)
        y = 0;
    if (x + g_dragging.clientWidth >= ~~((g_dashboard_left + g_dashboard_width) / grid_size.x) * grid_size.x)
        x = ~~((g_dashboard_width - g_dragging.clientWidth) / grid_size.x) * grid_size.x;
    if (y + g_dragging.clientHeight >= ~~((g_dashboard_top + g_dashboard_height) / grid_size.y) * grid_size.y)
        y = ~~((g_dashboard_height - g_dragging.clientHeight) / grid_size.y) * grid_size.y;

    // convert x/y coords to grid coords and save info in dashlets construct
    // which is then used to peform the dynamic dashlet sizing
    compute_dashlet_coords(nr, null, new vec(x / grid_size.x, y / grid_size.y));
    size_dashlets();
}

function drag_dashlet_stop(event) {
    if (!event)
        event = window.event;

    if (!g_dragging)
        return true;

    edit_visualize(g_dragging, false);
    var nr = parseInt(g_dragging.id.replace('dashlet_', ''));
    g_dragging = false;

    persist_dashlet_pos(nr);

    return false;
}

function persist_dashlet_pos(nr) {
    get_url('ajax_dashlet_pos.py?name=' + dashboard_name + '&id=' + nr
            + '&x=' + dashlets[nr].x + '&y=' + dashlets[nr].y
            + '&w=' + dashlets[nr].w + '&h=' + dashlets[nr].h,
            handle_dashlet_post_response, undefined, null, false);
}

function handle_dashlet_post_response(_unused, response_text) {
    var parts = response_text.split(' ');
    if (parts[0] != 'OK') {
        alert('Error: ' + response_text);
    } else {
        dashboard_mtime = parseInt(parts[1]);
    }
}

function edit_visualize(obj, show) {
    if (show)
        obj.style.zIndex = 80;
    else
        obj.style.zIndex = 1;
}

/**
 * Resizing of dashlets
 */

// false or the resizer dom object currently being worked with
var g_resizing     = false;
var g_resize_start = null;

function resize_dashlet_start(event) {
    if (!event)
        event = window.event;

    if (!g_editing)
        return true;

    var target = getTarget(event);
    var button = getButton(event);

    if (g_resizing === false && button == 'LEFT' && has_class(target, 'resize')) {
        var dashlet_obj = target.parentNode.parentNode;
        var nr = parseInt(dashlet_obj.id.replace('dashlet_', ''));

        g_resizing = target;
        g_resize_start = [
            event.clientX, event.clientY,   // mouse position
            dashlet_obj.offsetLeft, dashlet_obj.offsetTop, // initial pos
            dashlet_obj.clientWidth, dashlet_obj.clientHeight // initial size
        ];

        edit_visualize(dashlet_obj, true);

        prevent_default_events(event);
        return false;
    }
    return true;
}

function resize_dashlet(event) {
    if (!event)
        event = window.event;

    if (!g_resizing)
        return true;

    var dashlet_obj = g_resizing.parentNode.parentNode;
    var nr = parseInt(dashlet_obj.id.replace('dashlet_', ''));

    var diff_x = ~~(Math.abs(g_resize_start[0] - event.clientX) / grid_size.x) * grid_size.x;
    var diff_y = ~~(Math.abs(g_resize_start[1] - event.clientY) / grid_size.x) * grid_size.x;

    if (event.clientX > g_resize_start[0])
        diff_x *= -1;
    if (event.clientY > g_resize_start[1])
        diff_y *= -1;

    var board_w = ~~((g_dashboard_left + g_dashboard_width) / grid_size.y) * grid_size.y;
    var board_h = ~~((g_dashboard_top + g_dashboard_height) / grid_size.y) * grid_size.y;

    if (has_class(g_resizing, 'resize0_0')) {
        // resizing to left
        if (g_resize_start[2] - diff_x < 0) {
            // reached left border
            dashlet_obj.style.left  = 0;
            dashlet_obj.style.width = (g_resize_start[4] + g_resize_start[2]) + 'px';
        }
        else {
            dashlet_obj.style.left  = (g_resize_start[2] - diff_x) + 'px';
            dashlet_obj.style.width = (g_resize_start[4] + diff_x) + 'px';
        }
    }
    else if (has_class(g_resizing, 'resize0_1')) {
        // resizing to right
        if (g_resize_start[2] + g_resize_start[4] - diff_x > board_w) {
            // reached right border
            dashlet_obj.style.width = (board_w - g_resize_start[2]) + 'px';
        }
        else {
            dashlet_obj.style.width = (g_resize_start[4] - diff_x) + 'px';
        }
    }
    else if (has_class(g_resizing, 'resize1_0')) {
        // resizing to top
        if (g_resize_start[3] - diff_y < 0) {
            // reached top border
            dashlet_obj.style.top = 0;
            dashlet_obj.style.height = (g_resize_start[5] + g_resize_start[3]) + 'px';
        }
        else {
            dashlet_obj.style.top    = (g_resize_start[3] - diff_y) + 'px';
            dashlet_obj.style.height = (g_resize_start[5] + diff_y) + 'px';
        }
    }
    else if (has_class(g_resizing, 'resize1_1')) {
        // resizing to bottom
        if (g_resize_start[3] + g_resize_start[5] - diff_y >= board_h) {
            // reached bottom border
            dashlet_obj.style.height = (board_h - g_resize_start[3]) + 'px';
        }
        else {
            dashlet_obj.style.height = (g_resize_start[5] - diff_y) + 'px';
        }
    }

    // Apply minimum size limits
    if (dashlet_obj.clientWidth < 150)
        dashlet_obj.style.width = '150px';
    if (dashlet_obj.clientHeight < 70)
        dashlet_obj.style.height = '70px';

    // Set the size in coord structure
    dashlets[nr].w = dashlet_obj.clientWidth / grid_size.x;
    dashlets[nr].h = dashlet_obj.clientHeight / grid_size.y;

    // Set the position in coord structure
    compute_dashlet_coords(nr, null, new vec(dashlet_obj.offsetLeft / grid_size.x,
                                             dashlet_obj.offsetTop / grid_size.y));

    size_dashlets();
}

function resize_dashlet_stop(event) {
    if (!event)
        event = window.event;

    if (!g_resizing)
        return true;

    var dashlet_obj = g_resizing.parentNode.parentNode;
    var nr = parseInt(dashlet_obj.id.replace('dashlet_', ''));
    edit_visualize(dashlet_obj, false);
    g_resizing = false;

    dashlet_resized(nr, dashlet_obj);
    persist_dashlet_pos(nr);
    return false;
}

function dashlet_resized(nr, dashlet_obj) {
    if (typeof reload_on_resize[nr] != 'undefined') {
        var base_url = reload_on_resize[nr];
        var iframe = document.getElementById("dashlet_iframe_" + nr);
        iframe.src = base_url + '&width=' + dashlet_obj.clientWidth
                              + '&height=' + dashlet_obj.clientHeight;
        iframe = null;
    }

    if (typeof on_resize_dashlets[nr] != 'undefined') {
        on_resize_dashlets[nr]();
    }
}

/*
 * Register the global event handlers, used for dragging of dashlets,
 * dialog control and resizing of dashlets
 */

add_event_handler('mousemove', function(e) {
    return drag_dashlet(e) && resize_dashlet(e);
});
add_event_handler('mousedown', function(e) {
    return drag_dashlet_start(e) && resize_dashlet_start(e);
});
add_event_handler('mouseup', function(e) {
    return drag_dashlet_stop(e) && resize_dashlet_stop(e);
});
add_event_handler('click', function(e) {
    return body_click_handler(e);
});

// Totally disable the context menu for the dashboards in edit mode
add_event_handler('contextmenu', function(e) {
    if (g_editing) {
        prevent_default_events(e);
        return false;
    }
    else {
        return true;
    }
});
