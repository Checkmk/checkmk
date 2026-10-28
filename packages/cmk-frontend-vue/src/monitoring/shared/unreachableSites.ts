/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

export function unreachableSitesHeading(sites: readonly string[]): TranslatedString {
  const { _tn } = usei18n()
  return _tn('1 site is not reachable', '%{count} sites are not reachable', sites.length, {
    count: sites.length
  })
}

export function unreachableSitesHint(sites: readonly string[]): TranslatedString {
  const { _tn } = usei18n()
  return _tn(
    'No data could be retrieved from site %{sites}.',
    'No data could be retrieved from sites %{sites}.',
    sites.length,
    { sites: sites.join(', ') }
  )
}
