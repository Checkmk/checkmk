/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Folder, Page } from '@ucl/_ucl/types/page'

import UclTableCellBreakpoints from './UclTableCellBreakpoints.vue'
import UclBaseCell from './cell/UclBaseCell.vue'

export const pages: Array<Folder | Page> = [
  new Folder('Cell types', [new Page('BaseCell', UclBaseCell)]),
  new Page('Table Cell breakpoints', UclTableCellBreakpoints)
]
