/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { ValidationIssue } from '../formula'

export interface FormulaMessages {
  issueMessage: (issue: ValidationIssue) => TranslatedString
}

export function useFormulaMessages(): FormulaMessages {
  const { _t } = usei18n()

  function issueMessage(issue: ValidationIssue): TranslatedString {
    switch (issue.code) {
      case 'unknown-ref':
        return _t('Unknown metric or formula "%{id}".', { id: issue.id })
      case 'self-ref':
        return _t('The formula cannot reference itself ("%{id}").', { id: issue.id })
      case 'cyclic-ref':
        return _t('"%{id}" refers back to this formula (circular reference).', { id: issue.id })
      case 'domain-mismatch':
        return _t('Cannot mix RRD and metrics backend data: "%{id}".', { id: issue.id })
      case 'needs-consolidation':
        return _t('Consolidate "%{id}" using avg, min, max or sum.', { id: issue.id })
    }
  }

  return { issueMessage }
}
