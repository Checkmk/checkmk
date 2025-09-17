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

export const useAdditionalOptions = (): UseAdditionalOptions => {
  const metricColor = ref<DefaultOrColor>('default')
  const averageColor = ref<DefaultOrColor>('default')
  const medianColor = ref<DefaultOrColor>('default')

  return {
    metricColor,
    averageColor,
    medianColor
  }
}
