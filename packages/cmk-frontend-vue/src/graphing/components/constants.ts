/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// Frame padding between the plot's drawn edge and the figure's edge, on every side. An axis
// claims its own room on top of this, so hiding one leaves the padding standing and the plot
// stays centred in the figure.
export const PLOT_INSET_X = 10
export const PLOT_INSET_Y = 4

// The room the value axis claims inside the frame padding when nothing configures it. A graph
// whose tick labels need more widens it (see TimeSeriesGraph).
export const VALUE_AXIS_ROOM_MIN = 40

// Where axisLeft puts a value label: its right edge sits this far left of the plot, being d3's
// default tickSize plus tickPadding.
export const VALUE_LABEL_TICK_OFFSET = 9

// What a default graph spends horizontally on frame padding and value-axis room. Sizes fetches
// and seeds the brush track before the renderer reports the inset it settled on.
export const CANVAS_MARGIN_LEFT = PLOT_INSET_X + VALUE_AXIS_ROOM_MIN
export const CANVAS_MARGIN_HORIZONTAL = CANVAS_MARGIN_LEFT + PLOT_INSET_X

export const MIN_ZOOM_TIME_RANGE_SECONDS = 180

export const LEADING_NEIGHBOUR_STEPS = 2
export const TRAILING_NEIGHBOUR_STEPS = 1

export const BOTTOM_SCREEN_MARGIN = 40
