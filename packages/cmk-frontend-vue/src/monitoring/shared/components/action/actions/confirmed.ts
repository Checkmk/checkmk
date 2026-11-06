/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { MonitoringAction } from '../types'
import { commandFailed } from './feedback'

export interface ConfirmedKindConfig<Target> {
  run(targets: Target[]): Promise<number>
  successMessage(count: number): TranslatedString
  errorHeading: TranslatedString
}

/** An action without input that asks for confirmation in the alert above the table. */
export function createConfirmedAction<Target>(
  base: Pick<MonitoringAction<Record<string, never>, Target>, 'id' | 'title' | 'confirm'>,
  config: ConfirmedKindConfig<Target>
): MonitoringAction<Record<string, never>, Target> {
  return {
    ...base,
    submitLabel: base.title,
    defaultValues: () => ({}),
    perform: async (targets: Target[]) => {
      try {
        const count = await config.run(targets)
        return { variant: 'success', message: config.successMessage(count) }
      } catch {
        return commandFailed(config.errorHeading)
      }
    }
  }
}
