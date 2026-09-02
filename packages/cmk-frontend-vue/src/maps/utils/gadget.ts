/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Default render size (px) for gauge/bar/trafficlight gadgets when an object
 * carries no explicit `display.image_size`. Larger than the icon default so the
 * gauge arc and value text stay legible — kept in one place so the canvases and
 * the size field's placeholder agree on what "default" means.
 */
export const GADGET_DEFAULT_SIZE = 60
