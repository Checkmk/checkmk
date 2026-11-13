/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import type { GraphLegend } from '@/dashboard/components/Wizard/types'

interface StoredGraphLegend {
  legend?: GraphLegend
}

export interface UseGraphLegend {
  graphLegend: Ref<GraphLegend>
}

export const useGraphLegend = (
  stored: StoredGraphLegend | undefined,
  isNewWidget: boolean
): UseGraphLegend => ({
  graphLegend: ref<GraphLegend>(isNewWidget ? 'compact' : (stored?.legend ?? 'none'))
})
