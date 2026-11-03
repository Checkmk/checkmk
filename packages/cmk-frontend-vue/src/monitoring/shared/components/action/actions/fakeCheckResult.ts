/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import {
  FakeCheckResultApi,
  type FakeCheckResultOptions
} from '@/monitoring/shared/api/actions/fakeCheckResult'

import type { ActionTargetKind, MonitoringAction } from '../types'
import FakeCheckResultForm, { type FakeCheckResultValues } from './FakeCheckResultForm.vue'
import { commandFailed } from './feedback'

export const FAKE_CHECK_RESULT_ACTION_ID = 'fake_check_result'

export interface FakeCheckResultKindConfig<Target> {
  targetKind: ActionTargetKind
  fake(api: FakeCheckResultApi, targets: Target[], options: FakeCheckResultOptions): Promise<number>
  successMessage(count: number): TranslatedString
  errorHeading: TranslatedString
}

/** Shared fake check result flow for hosts and services: only the API call and wording differ. */
export function createFakeCheckResultAction<Target>(
  config: FakeCheckResultKindConfig<Target>
): MonitoringAction<FakeCheckResultValues, Target> {
  const { _t } = usei18n()
  const api = new FakeCheckResultApi()

  return {
    id: FAKE_CHECK_RESULT_ACTION_ID,
    title: _t('Fake check results'),
    submitLabel: _t('Fake check result'),
    form: FakeCheckResultForm,
    formProps: { targetKind: config.targetKind },
    // Like the legacy command, it starts from the good state: UP or OK.
    defaultValues: () => ({ state: 0, pluginOutput: '', metrics: '' }),
    perform: async (targets: Target[], values: FakeCheckResultValues) => {
      try {
        const count = await config.fake(api, targets, values)
        return { variant: 'success', message: config.successMessage(count) }
      } catch {
        return commandFailed(config.errorHeading)
      }
    }
  }
}
