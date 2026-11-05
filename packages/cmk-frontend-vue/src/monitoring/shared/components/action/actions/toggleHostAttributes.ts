/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { ModifiableAttribute } from '@/monitoring/shared/api/actions/modifiedAttributes'
import type { HostRef } from '@/monitoring/shared/api/types'
import {
  type ToggleActions,
  createToggleAttributeAction,
  toggleActionsByCommand
} from '@/monitoring/shared/components/action/actions/toggleAttribute'

/** Enabling and disabling notifications, active and passive checks of the selected hosts. */
export function useToggleHostAttributesActions(): ToggleActions<HostRef> {
  const { _t, _tn } = usei18n()
  const successMessages: Record<
    ModifiableAttribute,
    (count: number, enabled: boolean) => TranslatedString
  > = {
    notifications: (count, enabled) =>
      enabled
        ? _tn(
            'Enabled notifications for the selected host',
            'Enabled notifications for the selected hosts',
            count
          )
        : _tn(
            'Disabled notifications for the selected host',
            'Disabled notifications for the selected hosts',
            count
          ),
    active_checks: (count, enabled) =>
      enabled
        ? _tn(
            'Enabled active checks for the selected host',
            'Enabled active checks for the selected hosts',
            count
          )
        : _tn(
            'Disabled active checks for the selected host',
            'Disabled active checks for the selected hosts',
            count
          ),
    passive_checks: (count, enabled) =>
      enabled
        ? _tn(
            'Enabled passive checks for the selected host',
            'Enabled passive checks for the selected hosts',
            count
          )
        : _tn(
            'Disabled passive checks for the selected host',
            'Disabled passive checks for the selected hosts',
            count
          )
  }

  return toggleActionsByCommand((attribute) =>
    createToggleAttributeAction<HostRef>({
      attribute,
      toggle: (api, targets, toggled, enabled) => api.toggleHosts(targets, toggled, enabled),
      successMessage: successMessages[attribute],
      errorHeading: _t('Could not change the selected hosts')
    })
  )
}
