/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import type { DefaultOrColor } from '@/dashboard-wip/components/Wizard/types'

export interface UseAdditionalOptions {
  metricColor: Ref<DefaultOrColor>
  averageColor: Ref<DefaultOrColor>
  medianColor: Ref<DefaultOrColor>
}

export const useAdditionalOptions = (
  mColor: DefaultOrColor = 'default',
  aColor: DefaultOrColor = 'default',
  mdColor: DefaultOrColor = 'default'
): UseAdditionalOptions => {
  const metricColor = ref<DefaultOrColor>(mColor)
  const averageColor = ref<DefaultOrColor>(aColor)
  const medianColor = ref<DefaultOrColor>(mdColor)

  return {
    metricColor,
    averageColor,
    medianColor
  }
}
