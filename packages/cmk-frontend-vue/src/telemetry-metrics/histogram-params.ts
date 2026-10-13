/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { type ComputedRef, type WritableComputedRef, computed } from 'vue'

export const DEFAULT_QUANTILE = 0.95

// The rule form spec's own defaults, for the aggregation parameters a consolidation does not carry.
export const DEFAULT_HISTOGRAM_PERCENTILE = 90
export const DEFAULT_THRESHOLD_FOR_FRACTION_BELOW = 0
export const DEFAULT_LOWER_THRESHOLD_FOR_FRACTION_BETWEEN = 0
export const DEFAULT_UPPER_THRESHOLD_FOR_FRACTION_BETWEEN = 100

export interface HistogramParams {
  /** The quantile in the range 0–1 (default 0.95). */
  quantile?: number
  fractionBelowThreshold?: number
  fractionLowerThreshold?: number
  fractionUpperThreshold?: number
}

// A blank number input surfaces as NaN; fold non-finite values to undefined.
function normalizeNumber(value: number | undefined): number | undefined {
  return Number.isFinite(value) ? value : undefined
}

export interface HistogramParamInputs {
  quantileInput: WritableComputedRef<number | undefined>
  fractionBelowThresholdInput: WritableComputedRef<number | undefined>
  fractionLowerThresholdInput: WritableComputedRef<number | undefined>
  fractionUpperThresholdInput: WritableComputedRef<number | undefined>
  quantileErrors: ComputedRef<string[]>
  fractionBelowThresholdErrors: ComputedRef<string[]>
  fractionBetweenErrors: ComputedRef<string[]>
}

/**
 * Two-way inputs and validation for the histogram parameters, bound to a
 * model's `params` via a getter and a per-field setter.
 */
export function useHistogramParams(
  getParams: () => HistogramParams,
  setParam: (key: keyof HistogramParams, value: number | undefined) => void
): HistogramParamInputs {
  const { _t } = usei18n()

  const quantileInput = computed<number | undefined>({
    get: () => getParams().quantile,
    set: (value) => setParam('quantile', normalizeNumber(value))
  })
  const fractionBelowThresholdInput = computed<number | undefined>({
    get: () => getParams().fractionBelowThreshold,
    set: (value) => setParam('fractionBelowThreshold', normalizeNumber(value))
  })
  const fractionLowerThresholdInput = computed<number | undefined>({
    get: () => getParams().fractionLowerThreshold,
    set: (value) => setParam('fractionLowerThreshold', normalizeNumber(value))
  })
  const fractionUpperThresholdInput = computed<number | undefined>({
    get: () => getParams().fractionUpperThreshold,
    set: (value) => setParam('fractionUpperThreshold', normalizeNumber(value))
  })

  const quantileErrors = computed<string[]>(() => {
    const { quantile } = getParams()
    return quantile !== undefined && quantile >= 0 && quantile <= 1
      ? []
      : [_t('Enter a quantile between 0 and 1')]
  })

  const fractionBelowThresholdErrors = computed<string[]>(() =>
    getParams().fractionBelowThreshold === undefined ? [_t('Enter a threshold')] : []
  )

  // Cross-field: a per-input validator would miss the other bound's changes.
  const fractionBetweenErrors = computed<string[]>(() => {
    const { fractionLowerThreshold, fractionUpperThreshold } = getParams()
    if (fractionLowerThreshold === undefined || fractionUpperThreshold === undefined) {
      return [_t('Enter both thresholds')]
    }
    return fractionLowerThreshold < fractionUpperThreshold
      ? []
      : [_t('Lower threshold must be below the upper threshold')]
  })

  return {
    quantileInput,
    fractionBelowThresholdInput,
    fractionLowerThresholdInput,
    fractionUpperThresholdInput,
    quantileErrors,
    fractionBelowThresholdErrors,
    fractionBetweenErrors
  }
}
