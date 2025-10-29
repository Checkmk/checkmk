/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'

const { _t } = usei18n()

export const firstOperatorSuggestions = [
  { name: 'and', title: _t('is') },
  { name: 'not', title: _t('is not') }
]

export const operatorSuggestions = [
  { name: 'and', title: _t('and') },
  { name: 'or', title: _t('or') },
  { name: 'not', title: _t('and not') }
]
