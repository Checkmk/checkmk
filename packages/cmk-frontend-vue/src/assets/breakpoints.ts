/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * The responsive breakpoint scale in px, for layout decisions made in script. See
 * breakpoints.scss for the full KEEP IN SYNC list and the SCSS mixin API.
 */
export const BREAKPOINTS = {
  xs: 280,
  s: 535,
  m: 705,
  l: 961,
  xl: 1217
} as const
