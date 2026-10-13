/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { ActionFeedback } from '../ActionFeedback.vue'

export function commandFailed(heading: TranslatedString): ActionFeedback {
  const { _t } = usei18n()
  return {
    variant: 'error',
    heading,
    message: _t('Retry the command. If it keeps failing, check whether the site is running.')
  }
}
