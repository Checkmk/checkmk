/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { ModifiableAttribute } from '@/monitoring/shared/api/actions/modifiedAttributes'
import type { ServiceRef } from '@/monitoring/shared/api/types'
import { type ToggleAttributeValues } from '@/monitoring/shared/components/action/actions/ToggleAttributeForm.vue'
import { createToggleAttributeAction } from '@/monitoring/shared/components/action/actions/toggleAttribute'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

/** Enabling and disabling notifications, active and passive checks of the selected services. */
export function useToggleServiceAttributesActions(): MonitoringAction<
  ToggleAttributeValues,
  ServiceRef
>[] {
  const { _t, _tn } = usei18n()
  const successMessages: Record<
    ModifiableAttribute,
    (count: number, enabled: boolean) => TranslatedString
  > = {
    notifications: (count, enabled) =>
      enabled
        ? _tn(
            'Enabled notifications for the selected service',
            'Enabled notifications for the selected services',
            count
          )
        : _tn(
            'Disabled notifications for the selected service',
            'Disabled notifications for the selected services',
            count
          ),
    active_checks: (count, enabled) =>
      enabled
        ? _tn(
            'Enabled active checks for the selected service',
            'Enabled active checks for the selected services',
            count
          )
        : _tn(
            'Disabled active checks for the selected service',
            'Disabled active checks for the selected services',
            count
          ),
    passive_checks: (count, enabled) =>
      enabled
        ? _tn(
            'Enabled passive checks for the selected service',
            'Enabled passive checks for the selected services',
            count
          )
        : _tn(
            'Disabled passive checks for the selected service',
            'Disabled passive checks for the selected services',
            count
          )
  }

  return (Object.keys(successMessages) as ModifiableAttribute[]).map((attribute) =>
    createToggleAttributeAction<ServiceRef>({
      attribute,
      toggle: (api, targets, toggled, enabled) => api.toggleServices(targets, toggled, enabled),
      successMessage: successMessages[attribute],
      errorHeading: _t('Could not change the selected services')
    })
  )
}
