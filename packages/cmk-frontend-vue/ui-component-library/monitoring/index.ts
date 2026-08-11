/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Folder, Page } from '@ucl/_ucl/types/page'

import UclActionFormPane from './UclActionFormPane.vue'
import UclColumnPicker from './UclColumnPicker.vue'
import UclColumnPinning from './UclColumnPinning.vue'
import UclEditableTable from './UclEditableTable.vue'
import UclMonitoringActionBar from './UclMonitoringActionBar.vue'
import UclMonitoringPagination from './UclMonitoringPagination.vue'
import UclRefreshCountdown from './UclRefreshCountdown.vue'
import UclTableCellBreakpoints from './UclTableCellBreakpoints.vue'
import UclTableColumnFilters from './UclTableColumnFilters.vue'
import UclActionsCell from './cell/UclActionsCell.vue'
import UclBaseCell from './cell/UclBaseCell.vue'
import UclCheckboxCell from './cell/UclCheckboxCell.vue'
import UclCollapsibleCell from './cell/UclCollapsibleCell.vue'
import UclColorPickerCell from './cell/UclColorPickerCell.vue'
import UclDragHandleCell from './cell/UclDragHandleCell.vue'
import UclDropdownCell from './cell/UclDropdownCell.vue'
import UclLabelCell from './cell/UclLabelCell.vue'
import UclModesCell from './cell/UclModesCell.vue'
import UclNumberCell from './cell/UclNumberCell.vue'
import UclPerfometerCell from './cell/UclPerfometerCell.vue'
import UclRichTextCell from './cell/UclRichTextCell.vue'
import UclStateCell from './cell/UclStateCell.vue'
import UclStringCell from './cell/UclStringCell.vue'
import UclSwitchCell from './cell/UclSwitchCell.vue'
import UclVisibilityCell from './cell/UclVisibilityCell.vue'

export const pages: Array<Folder | Page> = [
  new Folder('Cell types', [
    new Page('ActionsCell', UclActionsCell),
    new Page('BaseCell', UclBaseCell),
    new Page('CheckboxCell', UclCheckboxCell),
    new Page('CollapsibleCell', UclCollapsibleCell),
    new Page('ColorPickerCell', UclColorPickerCell),
    new Page('DragHandleCell', UclDragHandleCell),
    new Page('DropdownCell', UclDropdownCell),
    new Page('LabelCell', UclLabelCell),
    new Page('ModesCell', UclModesCell),
    new Page('NumberCell', UclNumberCell),
    new Page('PerfometerCell', UclPerfometerCell),
    new Page('RichTextCell', UclRichTextCell),
    new Page('StateCell', UclStateCell),
    new Page('StringCell', UclStringCell),
    new Page('SwitchCell', UclSwitchCell),
    new Page('VisibilityCell', UclVisibilityCell)
  ]),
  new Page('ActionFormPane', UclActionFormPane),
  new Page('MonitoringActionBar', UclMonitoringActionBar),
  new Page('MonitoringPagination', UclMonitoringPagination),
  new Page('RefreshCountdown', UclRefreshCountdown),
  new Page('Editable table', UclEditableTable),
  new Page('Table cell breakpoints', UclTableCellBreakpoints),
  new Page('Table column pinning', UclColumnPinning),
  new Page('Table column filters', UclTableColumnFilters),
  new Page('Column picker', UclColumnPicker)
]
