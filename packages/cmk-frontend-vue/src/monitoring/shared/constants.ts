/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DateTimePickerSettings } from 'cmk-ui-library/components/date-time/types'

export const DEFAULT_BATCH_SIZE = 1000
export const POLL_INTERVAL_MS = 30_000

export const ACTION_REFRESH_DELAY_MS = 1000

export const ACTION_DATE_TIME_SETTINGS: DateTimePickerSettings = { hourCycle: 24 }
export const ACTION_PANE_MIN_WIDTH = '520px'
