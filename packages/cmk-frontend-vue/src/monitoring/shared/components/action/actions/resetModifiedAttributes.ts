/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MonitoringActionIdent } from 'cmk-shared-typing/typescript/monitoring/action_ident'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { MonitoringAction } from '../types'
import { type ConfirmedKindConfig, createConfirmedAction } from './confirmed'

export const RESET_MODIFIED_ATTRIBUTES_ACTION_ID =
  'clear_modified_attributes' satisfies MonitoringActionIdent

/** Resets what enabling and disabling changed for the targets, back to their configuration. */
export function createResetModifiedAttributesAction<Target>(
  config: ConfirmedKindConfig<Target>
): MonitoringAction<Record<string, never>, Target> {
  const { _t } = usei18n()
  return createConfirmedAction(
    {
      id: RESET_MODIFIED_ATTRIBUTES_ACTION_ID,
      title: _t('Reset modified attributes'),
      confirm: {
        detail: () =>
          _t(
            "Resets the commands 'Enable/disable active checks', 'Enable/disable passive checks' and 'Enable/disable notifications' to the default state."
          ),
        submitLabel: () => _t('Reset attributes')
      }
    },
    config
  )
}
