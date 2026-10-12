/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { HostState, MonitoringState } from '@/dashboard/types/widget'

const { _t } = usei18n()

export type HostOrServiceStateKind = HostState | MonitoringState | 'PENDING'

/** The state to show, with PENDING for a host or service that was never checked. */
export function hostOrServiceStateKind(
  state: HostState | MonitoringState,
  hasBeenChecked: boolean
): HostOrServiceStateKind {
  return hasBeenChecked ? state : 'PENDING'
}

export const HOST_OR_SERVICE_STATE_COLOR: Record<HostOrServiceStateKind, string> = {
  UP: 'var(--color-state-ok)',
  OK: 'var(--color-state-ok)',
  WARNING: 'var(--color-state-warning)',
  DOWN: 'var(--color-state-critical)',
  CRITICAL: 'var(--color-state-critical)',
  UNREACHABLE: 'var(--color-state-unknown)',
  UNKNOWN: 'var(--color-state-unknown)',
  PENDING: 'var(--color-state-pending)'
}

/** The short label of a state, as the legacy state widgets show it. */
export function shortHostOrServiceState(kind: HostOrServiceStateKind): TranslatedString {
  switch (kind) {
    case 'UP':
      return _t('UP')
    case 'OK':
      return _t('OK')
    case 'WARNING':
      return _t('WARN')
    case 'DOWN':
      return _t('DOWN')
    case 'CRITICAL':
      return _t('CRIT')
    case 'UNREACHABLE':
      return _t('UNREACH')
    case 'UNKNOWN':
      return _t('UNKN')
    case 'PENDING':
      return _t('PEND')
  }
}
