/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { selectOrdinalForm } from 'cmk-ui-library/lib/i18n/pluralForm'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { type Formula, isArithmetic, serializeFormula } from '../calculation/formula'
import type { GraphItem, ScalarItem } from '../types'

export function useItemDescription() {
  const { _t, _tp, currentLanguage } = usei18n()

  function scalarName(scalarType: ScalarItem['scalar_type']): TranslatedString {
    switch (scalarType) {
      case 'warning':
        return _t('Warning')
      case 'critical':
        return _t('Critical')
      case 'warning_lower':
        return _t('Warning lower')
      case 'critical_lower':
        return _t('Critical lower')
      case 'min':
        return _t('Minimum')
      case 'max':
        return _t('Maximum')
    }
  }

  function describeFormula(ast: Formula): TranslatedString {
    if (ast.op === 'percentile') {
      const n = ast.percentile
      const operand = describeFormula(ast.operand)
      return selectOrdinalForm(n, currentLanguage.value, {
        one: () => _tp('ordinal one', '%{n}st percentile of %{operand}', { n, operand }),
        two: () => _tp('ordinal two', '%{n}nd percentile of %{operand}', { n, operand }),
        few: () => _tp('ordinal few', '%{n}rd percentile of %{operand}', { n, operand }),
        many: () => _tp('ordinal many', '%{n}th percentile of %{operand}', { n, operand }),
        other: () => _tp('ordinal other', '%{n}th percentile of %{operand}', { n, operand })
      })
    }
    if (isArithmetic(ast)) {
      return untranslated(serializeFormula(ast))
    }
    return untranslated('')
  }

  /** Detail label for an item: `= A + B`, `95th percentile of B`, `host > service > metric`, … */
  function describeItem(item: GraphItem): TranslatedString {
    switch (item.type) {
      case 'rrd_metric':
        return untranslated(`${item.host_name} > ${item.service_name} > ${item.metric_name}`)
      case 'scalar':
        return untranslated(
          `${item.host_name} > ${item.service_name} > ${item.metric_name} > ${scalarName(item.scalar_type)}`
        )
      case 'rrd_query':
        return untranslated(`${_t('Host filter')} > ${_t('Service filter')} > ${item.metric_name}`)
      case 'constant':
        return untranslated(`${_t('Constant')} ${item.value}`)
      case 'telemetry_metrics':
        return untranslated(item.metric_name)
      case 'rrd_formula':
        return item.ast.op === 'percentile'
          ? describeFormula(item.ast)
          : untranslated(`= ${describeFormula(item.ast)}`)
    }
  }

  return { describeFormula, describeItem }
}
