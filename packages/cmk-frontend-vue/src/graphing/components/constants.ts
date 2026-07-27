/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// Left, right, and total horizontal margin
export const CANVAS_MARGIN_LEFT = 50
export const CANVAS_MARGIN_RIGHT = 10
export const CANVAS_MARGIN_HORIZONTAL = CANVAS_MARGIN_LEFT + CANVAS_MARGIN_RIGHT

// The backend floors the RRD step at 60s (cmk/gui/graphing/_fetch_time_series.py), so a
// shorter window would request a resolution that cannot be served.
export const MIN_ZOOM_TIME_RANGE_SECONDS = 60
