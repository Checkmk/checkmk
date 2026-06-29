/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import { type Magnitude, formatTimeSpan } from '@/components/user-input/CmkTimeSpan/timeSpan'

import type { ConsolidationFunction, ConsolidationModel, MetricType } from './types'

const DEFAULT_QUANTILE = 0.95

const LOOKBACK_MAGNITUDES: Magnitude[] = ['hour', 'minute', 'second']

// Built at call time, not module load, because i18n is not yet set up then.
function functionLabels(): Record<
  MetricType,
  Partial<Record<ConsolidationFunction, TranslatedString>>
> {
  const { _t } = usei18n()
  return {
    gauge: {
      last_value: _t('Last recorded value'),
      avg: _t('Avg'),
      max: _t('Max'),
      min: _t('Min')
    },
    sum: {
      rate: _t('Rate'),
      delta: _t('Delta'),
      last_value: _t('Last recorded value (raw counter)')
    },
    histogram: {
      preserve_histogram: _t('Preserve histograms'),
      count_delta: _t('Count delta'),
      count_rate: _t('Count rate'),
      sum_delta: _t('Sum delta'),
      sum_rate: _t('Sum rate'),
      quantile: _t('Quantile'),
      frac_below: _t('Fraction below'),
      frac_between: _t('Fraction between'),
      last_value: _t('Cumulative sum field (raw)')
    }
  }
}

/** Full label for a function as shown in the dropdown. */
export function functionLabel(type: MetricType, fn: ConsolidationFunction): string {
  return functionLabels()[type][fn] ?? fn
}

/** Compact function token for the pill, e.g. 'rate', 'p95', 'fraction 0.1–0.9'. */
export function compactFunction(model: ConsolidationModel): string {
  const { _t } = usei18n()
  switch (model.function) {
    case 'last_value':
      return model.type === 'gauge' ? _t('last') : _t('raw')
    case 'avg':
      return _t('avg')
    case 'max':
      return _t('max')
    case 'min':
      return _t('min')
    case 'rate':
      return _t('rate')
    case 'delta':
      return _t('delta')
    case 'preserve_histogram':
      return _t('preserve histograms')
    case 'count_delta':
      return _t('count delta')
    case 'count_rate':
      return _t('count rate')
    case 'sum_delta':
      return _t('sum delta')
    case 'sum_rate':
      return _t('sum rate')
    case 'quantile': {
      // Keep up to two decimals so high quantiles read 'p99.9' rather than
      // rounding to a meaningless 'p100'.
      const percentile = +((model.params.quantile ?? DEFAULT_QUANTILE) * 100).toFixed(2)
      return `p${percentile}`
    }
    case 'frac_below':
      return _t('fraction <%{value}', { value: model.params.fracBelow ?? '?' })
    case 'frac_between':
      return _t('fraction %{lower}–%{upper}', {
        lower: model.params.fracLower ?? '?',
        upper: model.params.fracUpper ?? '?'
      })
  }
}

/**
 * Compact lookback for the read-only pill, e.g. '5 m' or '1 h 30 m'. The units
 * are abbreviated to keep the summary short; the edit controls (CmkTimeSpan)
 * spell them out in full.
 */
export function lookbackLabel(seconds: number): string {
  const { _tp } = usei18n()
  const label = formatTimeSpan(seconds, LOOKBACK_MAGNITUDES, {
    hour: _tp('Abbreviation for hours', 'h'),
    minute: _tp('Abbreviation for minutes', 'm'),
    second: _tp('Abbreviation for seconds', 's')
  })
  // formatTimeSpan omits magnitudes below the value, so a zero lookback yields
  // an empty label; fall back to seconds so the pill never renders empty.
  return label || `0 ${_tp('Abbreviation for seconds', 's')}`
}
