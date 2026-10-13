/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export type RequestedLimit = number | null

/** A `strftime`-style pattern, one of the fixed choices the display-options pane offers. */
export type DateFormatId = '%Y-%m-%d' | '%d.%m.%Y' | '%m/%d/%Y' | '%d.%m.' | '%m/%d'

export type TimestampFormatId = 'mixed' | 'abs' | 'rel' | 'both' | 'epoch'

/** How `last_check` / `last_state_change` timestamps render, set via the "Modify display options" pane. */
export interface DisplayOptions {
  dateFormat: DateFormatId
  timestampFormat: TimestampFormatId
}

export const DEFAULT_DISPLAY_OPTIONS: DisplayOptions = {
  dateFormat: '%Y-%m-%d',
  timestampFormat: 'mixed'
}
