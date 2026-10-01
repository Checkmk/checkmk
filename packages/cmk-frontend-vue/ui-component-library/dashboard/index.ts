/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Page } from '@ucl/_ucl/types/page'

import UclCmkGaugeFigure from './CmkGaugeFigure/UclCmkGaugeFigure.vue'
import UclCmkInventoryFigure from './CmkInventoryFigure/UclCmkInventoryFigure.vue'
import UclCmkKpiStatCard from './CmkKpiStatCard/UclCmkKpiStatCard.vue'
import UclCmkRankedTable from './CmkRankedTable/UclCmkRankedTable.vue'
import UclCmkStateFigure from './CmkStateFigure/UclCmkStateFigure.vue'
import UclCmkStateSummaryFigure from './CmkStateSummaryFigure/UclCmkStateSummaryFigure.vue'
import UclCmkStatsFigure from './CmkStatsFigure/UclCmkStatsFigure.vue'

export const pages: Array<Page> = [
  new Page('CmkGaugeFigure', UclCmkGaugeFigure),
  new Page('CmkInventoryFigure', UclCmkInventoryFigure),
  new Page('CmkKpiStatCard', UclCmkKpiStatCard),
  new Page('CmkRankedTable', UclCmkRankedTable),
  new Page('CmkStateFigure', UclCmkStateFigure),
  new Page('CmkStateSummaryFigure', UclCmkStateSummaryFigure),
  new Page('CmkStatsFigure', UclCmkStatsFigure)
]
