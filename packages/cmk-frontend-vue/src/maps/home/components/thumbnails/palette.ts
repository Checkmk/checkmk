/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The states the list illustrations paint.
 *
 * The colours themselves are custom properties ``MapThumbnail`` sets on the
 * frame, so the per-type illustrations inherit one palette instead of each
 * carrying its own: ``--maps-map-thumbnail-{ok,warn,crit,unknown}`` for the
 * monitoring states (the shared ``--color-state-*`` tokens) plus
 * ``--maps-map-thumbnail-{canvas,grid,edge,neutral,surface,border,label,on-state}``
 * for the chrome.
 */
export type ThumbnailState = 'ok' | 'warn' | 'crit'
