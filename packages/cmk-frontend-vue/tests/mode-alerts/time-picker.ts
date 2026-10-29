/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'

export const TIME_PICKER: GlobalTimePickerProps = {
  custom_time_ranges: [
    { title: 'Last 4 hours', total_seconds: 4 * 3600 },
    { title: 'Last 25 hours', total_seconds: 25 * 3600 }
  ],
  default_time_range: 4 * 3600,
  server_time_zone: 'UTC',
  first_day_of_week: null,
  refresh: {
    interval_seconds: null,
    interval_choices_seconds: [30, 60],
    starts_live: false,
    reloads_page_content: false
  }
}
