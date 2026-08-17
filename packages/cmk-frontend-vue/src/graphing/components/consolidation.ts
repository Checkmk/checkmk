/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type ComputedRef, computed } from 'vue'

export const CONSOLIDATION_FUNCTIONS = ['min', 'avg', 'max'] as const

export type ConsolidationFn = (typeof CONSOLIDATION_FUNCTIONS)[number]

// Mirrors what the backend consolidates with when a request names no function
// (cmk/gui/graphing/_graph_templates.py).
export const DEFAULT_CONSOLIDATION_FN: ConsolidationFn = 'max'

export function isConsolidationFn(value: string | null): value is ConsolidationFn {
  return CONSOLIDATION_FUNCTIONS.some((consolidationFunction) => consolidationFunction === value)
}

export function useConsolidationFunctionLabels(): ComputedRef<
  Record<ConsolidationFn, TranslatedString>
> {
  const { _t } = usei18n()
  return computed(() => ({
    min: _t('Min'),
    avg: _t('Average'),
    max: _t('Max')
  }))
}
