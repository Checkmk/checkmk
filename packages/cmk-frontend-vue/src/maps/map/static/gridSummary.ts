/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { MapElement, ObjectState } from '@/maps/types/api'
import { type I18n, objectTypeLabel } from '@/maps/utils/dropdownOptions'

export function gridCaption(
  i18n: I18n,
  grid: MapElement,
  state: ObjectState | undefined,
  shown: number
): string {
  return `${objectTypeLabel('grid', i18n._t)} · ${gridSummary(i18n, grid, state, shown)}`
}

function gridSummary(
  { _t, _tn }: I18n,
  grid: MapElement,
  state: ObjectState | undefined,
  shown: number
): TranslatedString {
  const services = grid.object_types === 'service'
  if (state?.stale) {
    return services
      ? _t('Could not read the matching services')
      : _t('Could not read the matching hosts')
  }
  if (state?.grid_truncated) {
    return _t('%{n} shown, more match', { n: shown })
  }
  if (shown === 0) {
    return services ? _t('No matching services') : _t('No matching hosts')
  }
  return services
    ? _tn('%{n} service', '%{n} services', shown, { n: shown })
    : _tn('%{n} host', '%{n} hosts', shown, { n: shown })
}
