/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { useFormulaMessages } from '../calculation/composables/useFormulaMessages'
import type { RowIssue } from '../validation'

export interface ValidationMessages {
  issueMessage: (issue: RowIssue) => TranslatedString
}

export function useValidationMessages(): ValidationMessages {
  const { _t } = usei18n()
  const { issueMessage: formulaIssueMessage } = useFormulaMessages()

  function issueMessage(issue: RowIssue): TranslatedString {
    switch (issue.code) {
      case 'required':
        return _t('This field is required.')
      case 'filter-required':
        return _t('Fill in at least one filter.')
      case 'not-finite':
        return _t('Enter a finite number.')
      case 'lookback-too-small':
        return _t('The lookback must be at least one second.')
      case 'percentile-out-of-range':
        return _t('The percentile must be between 0 and 100.')
      case 'thresholds-unordered':
        return _t('The lower threshold must be below the upper threshold.')
      case 'ref-incomplete':
        return _t('"%{id}" is not configured yet.', { id: issue.ref })
      case 'unknown-ref':
      case 'self-ref':
      case 'cyclic-ref':
      case 'domain-mismatch':
      case 'needs-consolidation':
        return formulaIssueMessage({ code: issue.code, id: issue.ref })
    }
  }

  return { issueMessage }
}
