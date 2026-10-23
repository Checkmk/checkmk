/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { type MarkerState, splitStateMarkers } from '@/monitoring/shared/stateMarkers'

/**
 * Spells each state marker in plugin output out as the translated name of the
 * state it stands for, for places that can show only plain text, such as a
 * tooltip.
 */
export function spellStateMarkers(output: string): string {
  const { _t } = usei18n()

  // The names the state filters of the monitoring tables give the states, not
  // the labels of the state badge that a marker is rendered as.
  function stateName(state: MarkerState): TranslatedString {
    switch (state) {
      case 'OK':
        return _t('OK')
      case 'WARN':
        return _t('WARN')
      case 'CRIT':
        return _t('CRIT')
      case 'UNKNOWN':
        return _t('UNKNOWN')
    }
  }

  return splitStateMarkers(output)
    .map((segment) => (segment.type === 'marker' ? `(${stateName(segment.state)})` : segment.text))
    .join('')
}
