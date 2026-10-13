/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { attributeKindLabel } from '../attribute-kind'
import { DEFAULT_QUANTILE } from '../histogram-params'
import {
  type AggregationStep,
  type GroupByFunction,
  type GroupByModel,
  type GroupKey,
  isKeyValid
} from './types'

// Built at call time, not module load, because i18n is not yet set up then.
function functionLabels(): Record<GroupByFunction, TranslatedString> {
  const { _t } = usei18n()
  return {
    none: _t('no grouping'),
    avg: _t('avg by'),
    min: _t('min by'),
    max: _t('max by'),
    sum: _t('sum by'),
    count: _t('count by'),
    percentile: _t('percentile by'),
    fraction_below: _t('fraction below by'),
    fraction_between: _t('fraction between by')
  }
}

export function functionLabel(fn: GroupByFunction): TranslatedString {
  return functionLabels()[fn] ?? untranslated(fn)
}

/** Group key label: '[Resource] service.name', or just the key while its kind is unset. */
export function keyPillLabel(key: GroupKey): string {
  const prefix = key.attributeKind === null ? '' : `[${attributeKindLabel(key.attributeKind)}] `
  return `${prefix}${key.attributeKey}`
}

/** Clause-head token for the collapsed chip, e.g. 'p95 by', 'fraction <0.1 by', 'avg by'. */
export function compactFunctionLabel(model: GroupByModel): string {
  const { _t } = usei18n()
  switch (model.function) {
    case 'percentile': {
      // Two decimals so high quantiles read 'p99.9', not a rounded 'p100'.
      const percentile = +((model.params.quantile ?? DEFAULT_QUANTILE) * 100).toFixed(2)
      return _t('p%{percentile} by', { percentile })
    }
    case 'fraction_below':
      return _t('fraction <%{value} by', { value: model.params.fractionBelowThreshold ?? '?' })
    case 'fraction_between':
      return _t('fraction %{lower}–%{upper} by', {
        lower: model.params.fractionLowerThreshold ?? '?',
        upper: model.params.fractionUpperThreshold ?? '?'
      })
    default:
      return functionLabel(model.function)
  }
}

/** Collapsed-chip summary: 'no grouping', '<function> [Kind] key, ...', or a keyless placeholder. */
export function clauseSummary(model: GroupByModel): string {
  const { _t } = usei18n()
  const fn = compactFunctionLabel(model)
  if (model.function === 'none') {
    return fn
  }
  if (model.keys.length === 0) {
    return `${fn} ${_t('nothing, combine all series into one')}`
  }
  return `${fn} ${model.keys.map(keyPillLabel).join(', ')}`
}

/** Then-step summary: 'then <function> [Kind] key, ...', or a keyless placeholder. */
export function thenStepSummary(step: AggregationStep): string {
  const { _t } = usei18n()
  const keys = step.keys.filter(isKeyValid)
  const tail =
    keys.length === 0
      ? _t('nothing, combine all series into one')
      : keys.map(keyPillLabel).join(', ')
  return `${_t('then')} ${functionLabel(step.function)} ${tail}`
}
