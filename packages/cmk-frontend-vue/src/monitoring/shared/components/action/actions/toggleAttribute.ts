/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MonitoringActionIdent } from 'cmk-shared-typing/typescript/monitoring/action_ident'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import {
  type ModifiableAttribute,
  ModifiedAttributesApi
} from '@/monitoring/shared/api/actions/modifiedAttributes'

import type { MonitoringAction } from '../types'
import ToggleAttributeForm, { type ToggleAttributeValues } from './ToggleAttributeForm.vue'
import { commandFailed } from './feedback'

/** The legacy command each attribute is switched by. */
export const TOGGLE_ACTION_IDS = {
  notifications: 'notifications',
  active_checks: 'toggle_active_checks',
  passive_checks: 'toggle_passive_checks'
} as const satisfies Readonly<Record<ModifiableAttribute, MonitoringActionIdent>>

export interface ToggleKindConfig<Target> {
  attribute: ModifiableAttribute
  toggle(
    api: ModifiedAttributesApi,
    targets: Target[],
    attribute: ModifiableAttribute,
    enabled: boolean
  ): Promise<number>
  successMessage(count: number, enabled: boolean): TranslatedString
  errorHeading: TranslatedString
}

/** Shared enable/disable flow for hosts and services: only the API call and wording differ. */
export function createToggleAttributeAction<Target>(
  config: ToggleKindConfig<Target>
): MonitoringAction<ToggleAttributeValues, Target> {
  const { _t } = usei18n()
  const api = new ModifiedAttributesApi()
  const texts: Record<ModifiableAttribute, { title: TranslatedString; label: TranslatedString }> = {
    notifications: { title: _t('Enable / Disable notifications'), label: _t('Notifications') },
    active_checks: { title: _t('Enable / Disable active checks'), label: _t('Active checks') },
    passive_checks: { title: _t('Enable / Disable passive checks'), label: _t('Passive checks') }
  }
  const { title, label } = texts[config.attribute]

  return {
    id: TOGGLE_ACTION_IDS[config.attribute],
    title,
    submitLabel: _t('Confirm'),
    form: ToggleAttributeForm,
    formProps: { label },
    defaultValues: () => ({ enabled: true }),
    perform: async (targets: Target[], { enabled }: ToggleAttributeValues) => {
      try {
        const count = await config.toggle(api, targets, config.attribute, enabled)
        return { variant: 'success', message: config.successMessage(count, enabled) }
      } catch {
        return commandFailed(config.errorHeading)
      }
    }
  }
}
