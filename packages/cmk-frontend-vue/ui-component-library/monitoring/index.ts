/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Folder, Page } from '@ucl/_ucl/types/page'

import UclActionFormPane from './UclActionFormPane.vue'
import UclColumnPinning from './UclColumnPinning.vue'
import UclMonitoringActionBar from './UclMonitoringActionBar.vue'
import UclRefreshCountdown from './UclRefreshCountdown.vue'
import UclTableCellBreakpoints from './UclTableCellBreakpoints.vue'
import UclTableColumnFilters from './UclTableColumnFilters.vue'
import UclActionsCell from './cell/UclActionsCell.vue'
import UclBaseCell from './cell/UclBaseCell.vue'
import UclCheckboxCell from './cell/UclCheckboxCell.vue'
import UclNumberCell from './cell/UclNumberCell.vue'
import UclStateCell from './cell/UclStateCell.vue'
import UclStringCell from './cell/UclStringCell.vue'

export const pages: Array<Folder | Page> = [
  new Folder('Cell types', [
    new Page('ActionsCell', UclActionsCell),
    new Page('BaseCell', UclBaseCell),
    new Page('CheckboxCell', UclCheckboxCell),
    new Page('NumberCell', UclNumberCell),
    new Page('StateCell', UclStateCell),
    new Page('StringCell', UclStringCell)
  ]),
  new Page('ActionFormPane', UclActionFormPane),
  new Page('MonitoringActionBar', UclMonitoringActionBar),
  new Page('RefreshCountdown', UclRefreshCountdown),
  new Page('Table cell breakpoints', UclTableCellBreakpoints),
  new Page('Table column pinning', UclColumnPinning),
  new Page('Table column filters', UclTableColumnFilters)
]
