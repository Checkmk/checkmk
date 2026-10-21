/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'

export function dateFormatChoices(): Suggestions {
  return {
    type: 'fixed',
    suggestions: [
      { name: '%Y-%m-%d', title: untranslated('1970-12-18') },
      { name: '%d.%m.%Y', title: untranslated('18.12.1970') },
      { name: '%m/%d/%Y', title: untranslated('12/18/1970') },
      { name: '%d.%m.', title: untranslated('18.12.') },
      { name: '%m/%d', title: untranslated('12/18') }
    ]
  }
}

export function timestampFormatChoices(): Suggestions {
  const { _t } = usei18n()
  return {
    type: 'fixed',
    suggestions: [
      { name: 'mixed', title: _t('Mixed') },
      { name: 'abs', title: _t('Absolute') },
      { name: 'rel', title: _t('Relative') },
      { name: 'both', title: _t('Both') },
      { name: 'epoch', title: _t('Unix timestamp (epoch)') }
    ]
  }
}
