/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n from 'cmk-ui-library/lib/i18n'

export function firstOperatorSuggestions(): Suggestion[] {
  const { _t } = usei18n()
  return [
    { name: 'and', title: _t('is') },
    { name: 'not', title: _t('is not') }
  ]
}

export function operatorSuggestions(): Suggestion[] {
  const { _t } = usei18n()
  return [
    { name: 'and', title: _t('and') },
    { name: 'or', title: _t('or') },
    { name: 'not', title: _t('and not') }
  ]
}
