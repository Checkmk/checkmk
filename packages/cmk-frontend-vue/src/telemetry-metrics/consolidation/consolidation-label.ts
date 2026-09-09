/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type Magnitude,
  formatTimeSpan
} from 'cmk-ui-library/components/user-input/CmkTimeSpan/timeSpan'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { DEFAULT_QUANTILE } from './types'
import type { ConsolidationFunctionName, ConsolidationModel, MetricType } from './types'

const LOOKBACK_MAGNITUDES: Magnitude[] = ['hour', 'minute', 'second']

// Built at call time, not module load, because i18n is not yet set up then.
function functionLabels(): Record<
  MetricType,
  Partial<Record<ConsolidationFunctionName, TranslatedString>>
> {
  const { _t } = usei18n()
  return {
    gauge: {
      gauge_last: _t('Last recorded value'),
      gauge_avg: _t('Avg'),
      gauge_max: _t('Max'),
      gauge_min: _t('Min')
    },
    sum: {
      sum_rate: _t('Rate'),
      sum_delta: _t('Delta'),
      sum_last_raw: _t('Last recorded value')
    },
    histogram: {
      histogram_preserve: _t('Preserve histograms'),
      histogram_count_delta: _t('Count delta'),
      histogram_count_rate: _t('Count rate'),
      histogram_sum_delta: _t('Sum delta'),
      histogram_sum_rate: _t('Sum rate'),
      histogram_quantile: _t('Quantile'),
      histogram_fraction_below: _t('Fraction below'),
      histogram_fraction_between: _t('Fraction between'),
      histogram_sum_raw: _t('Cumulative sum field')
    }
  }
}

/** Base label for a function, without the raw marker. */
export function functionLabel(type: MetricType, fn: ConsolidationFunctionName): TranslatedString {
  return functionLabels()[type][fn] ?? untranslated(fn)
}

/** Dropdown label for a function, appending a "(raw)" marker when raw. */
export function functionOptionLabel(
  type: MetricType,
  fn: ConsolidationFunctionName,
  raw: boolean
): TranslatedString {
  const { _t } = usei18n()
  const label = functionLabel(type, fn)
  return raw ? _t('%{label} (raw)', { label }) : label
}

/** Display name for a metric type. */
export function typeLabel(type: MetricType): TranslatedString {
  const { _t } = usei18n()
  const labels: Record<MetricType, TranslatedString> = {
    gauge: _t('Gauge'),
    sum: _t('Sum'),
    histogram: _t('Histogram')
  }
  return labels[type]
}

/** Compact function token for the pill, e.g. 'rate', 'p95', 'fraction 0.1–0.9'. */
export function compactFunction(model: ConsolidationModel): string {
  const { _t } = usei18n()
  switch (model.function) {
    case 'gauge_last':
      return _t('last')
    case 'sum_last_raw':
    case 'histogram_sum_raw':
      return _t('raw')
    case 'gauge_avg':
      return _t('avg')
    case 'gauge_max':
      return _t('max')
    case 'gauge_min':
      return _t('min')
    case 'sum_rate':
      return _t('rate')
    case 'sum_delta':
      return _t('delta')
    case 'histogram_preserve':
      return _t('preserve histograms')
    case 'histogram_count_delta':
      return _t('count delta')
    case 'histogram_count_rate':
      return _t('count rate')
    case 'histogram_sum_delta':
      return _t('sum delta')
    case 'histogram_sum_rate':
      return _t('sum rate')
    case 'histogram_quantile': {
      // Keep up to two decimals so high quantiles read 'p99.9' rather than
      // rounding to a meaningless 'p100'.
      const percentile = +((model.params.quantile ?? DEFAULT_QUANTILE) * 100).toFixed(2)
      return `p${percentile}`
    }
    case 'histogram_fraction_below':
      return _t('fraction <%{value}', { value: model.params.fractionBelowThreshold ?? '?' })
    case 'histogram_fraction_between':
      return _t('fraction %{lower}–%{upper}', {
        lower: model.params.fractionLowerThreshold ?? '?',
        upper: model.params.fractionUpperThreshold ?? '?'
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
