/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { HorizontalBarFigure } from '@/modules/figures/cmk_horizontal_bar'
import { PieChartFigure } from '@/modules/figures/cmk_pie_chart'

import { AlertOverview } from './cmk_alert_overview'
import { BarplotFigure } from './cmk_barplot'
import { figure_registry } from './cmk_figures'
import { GaugeFigure } from './cmk_gauge'
import { TableFigure } from './cmk_table'
import { TimeseriesFigure } from './timeseries/cmk_timeseries'

export function register() {
  figure_registry.register(TableFigure)
  figure_registry.register(AlertOverview)
  figure_registry.register(BarplotFigure)
  figure_registry.register(HorizontalBarFigure)
  figure_registry.register(GaugeFigure)
  figure_registry.register(PieChartFigure)
  figure_registry.register(TimeseriesFigure)
}
