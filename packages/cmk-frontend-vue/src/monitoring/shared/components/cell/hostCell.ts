/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { INLINE_STATE_TAG_WIDTH } from 'cmk-ui-library/components/stateTagSizes'

import { CELL_PADDING } from '../MonitoringTableContext'

// Each mirrors a width set in CSS, which points back here.
/** `HostCell`: the gap between the state tag and the name. */
const STATE_TAG_GAP = 4
/** `BaseCell`: the details icon an opening cell reserves, with its margins. */
const DETAILS_ICON_WIDTH = 4 + 16 + 4

/**
 * The width a `HostCell` that opens the host spends besides the host name. Too wide for a read-only
 * one, which reserves no details icon.
 */
export const HOST_CELL_CHROME =
  CELL_PADDING + INLINE_STATE_TAG_WIDTH + STATE_TAG_GAP + DETAILS_ICON_WIDTH
