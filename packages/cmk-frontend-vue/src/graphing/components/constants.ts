/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// Left, right, and total horizontal margin. The left margin is the narrowest the value
// axis gets; a graph whose tick labels need more room widens it (see TimeSeriesGraph).
export const CANVAS_MARGIN_LEFT = 50
export const CANVAS_MARGIN_RIGHT = 10
export const CANVAS_MARGIN_HORIZONTAL = CANVAS_MARGIN_LEFT + CANVAS_MARGIN_RIGHT

// Space between the widest value-axis label and the plot's left edge.
export const VALUE_LABEL_GUTTER = 10

export const MIN_ZOOM_TIME_RANGE_SECONDS = 180

export const BOTTOM_SCREEN_MARGIN = 40
