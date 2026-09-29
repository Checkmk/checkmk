/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'

import type { WidgetTimeRange } from '@/dashboard/types/widget'

/** The time range of a widget data request. */
export function widgetTimeRange(range: DateTimeRange): WidgetTimeRange {
  return { start: range.from.toAbsoluteString(), end: range.to.toAbsoluteString() }
}
