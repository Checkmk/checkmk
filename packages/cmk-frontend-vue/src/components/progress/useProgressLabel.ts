/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, computed } from 'vue'

export type ProgressLabel = { showTotal?: boolean; unit?: string } | boolean | undefined

export interface ProgressLabelProps {
  value: number
  max: number | 'unknown'
  label: ProgressLabel
}

export interface ProgressLabelState {
  accessibilityLabelString: ComputedRef<string>
  labelString: ComputedRef<string>
  progressRatio: ComputedRef<number>
}

export default function useProgressLabel(source: () => ProgressLabelProps): ProgressLabelState {
  const accessibilityLabelString = computed<string>(() => {
    const { value, max, label } = source()

    if (max === 'unknown' || typeof max === 'undefined') {
      return 'unknown progress'
    }

    if (label) {
      if (label !== true) {
        return `${value.toFixed(0)}${label?.showTotal ? ' / '.concat(max.toFixed(0)) : ''} ${label?.unit}`.trim()
      }
    }

    return value.toFixed(0)
  })

  const labelString = computed<string>(() => {
    if (source().label) {
      return accessibilityLabelString.value
    }

    return ''
  })

  const progressRatio = computed(() => {
    const { value, max } = source()
    return max === 'unknown' ? 0 : Math.min(Math.max(value / max, 0), 1)
  })

  return { accessibilityLabelString, labelString, progressRatio }
}
