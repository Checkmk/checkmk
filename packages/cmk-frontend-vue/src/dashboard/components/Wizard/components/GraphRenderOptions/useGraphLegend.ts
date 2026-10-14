/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import type { GraphLegendStyle } from '@/dashboard/components/Wizard/types'

interface StoredGraphLegend {
  show_legend?: boolean
  legend_style?: GraphLegendStyle
}

export interface UseGraphLegend {
  graphLegend: Ref<boolean>
  graphLegendStyle: Ref<GraphLegendStyle>
}

export const useGraphLegend = (
  stored: StoredGraphLegend | undefined,
  isNewWidget: boolean
): UseGraphLegend => {
  const graphLegend = ref<boolean>(isNewWidget ? true : (stored?.show_legend ?? false))
  const graphLegendStyle = ref<GraphLegendStyle>(stored?.legend_style ?? 'compact')
  return { graphLegend, graphLegendStyle }
}
