/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// What the user has chosen (drives GraphDateTimeRangePicker).
// Distinct from TimeRange, which is what the RRD actually returned.
export interface RequestedTimeRange {
  start: number // unix seconds
  end: number // unix seconds
}

interface BurgerMenuAction {
  label: string
  onClick: () => void
}

export interface BurgerMenuGroup {
  heading: string
  actions: BurgerMenuAction[]
}
