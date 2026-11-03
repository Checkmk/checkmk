/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { MonitoringAction } from '../types'
import { commandFailed } from './feedback'

export const REMOVE_ACK_ACTION_ID = 'remove_acknowledgments'
export const REMOVE_DOWNTIMES_ACTION_ID = 'remove_downtimes_hosts_services'

export interface RemoveKindConfig<Target> {
  remove(targets: Target[]): Promise<void>
  successMessage(count: number): TranslatedString
  errorHeading: TranslatedString
}

function createRemoveAction<Target>(
  base: Pick<MonitoringAction<Record<string, never>, Target>, 'id' | 'title' | 'confirm'>,
  config: RemoveKindConfig<Target>
): MonitoringAction<Record<string, never>, Target> {
  return {
    ...base,
    submitLabel: base.title,
    defaultValues: () => ({}),
    perform: async (targets: Target[]) => {
      try {
        await config.remove(targets)
        return { variant: 'success', message: config.successMessage(targets.length) }
      } catch {
        return commandFailed(config.errorHeading)
      }
    }
  }
}

/** Removes the acknowledgements of the targets, which the page narrows to acknowledged ones. */
export function createRemoveAcknowledgementsAction<Target>(
  config: RemoveKindConfig<Target>
): MonitoringAction<Record<string, never>, Target> {
  const { _t } = usei18n()
  return createRemoveAction(
    {
      id: REMOVE_ACK_ACTION_ID,
      title: _t('Remove acknowledgements'),
      confirm: {
        detail: (count) => _t('Acknowledgements: %{count}', { count }),
        submitLabel: () => _t('Remove acknowledgements')
      }
    },
    config
  )
}

/** Removes the downtimes of the targets, which the page narrows to ones in downtime. */
export function createRemoveDowntimesAction<Target>(
  config: RemoveKindConfig<Target>
): MonitoringAction<Record<string, never>, Target> {
  const { _t } = usei18n()
  return createRemoveAction(
    {
      id: REMOVE_DOWNTIMES_ACTION_ID,
      title: _t('Remove downtimes'),
      confirm: {
        detail: (count) => _t('Downtimes: %{count}', { count }),
        submitLabel: () => _t('Remove downtimes')
      }
    },
    config
  )
}

/** The mode a row shows while it has something for the removal to remove. */
const REMOVED_MODE: Readonly<Record<string, string>> = {
  [REMOVE_ACK_ACTION_ID]: 'acknowledged',
  [REMOVE_DOWNTIMES_ACTION_ID]: 'downtime'
}

/** Narrows the rows a removal acts on to those having something to remove; others keep all. */
export function rowsToActOn<Row extends { modes?: readonly { id: string }[] | undefined }>(
  rows: Row[],
  actionId: string
): Row[] {
  const mode = REMOVED_MODE[actionId]
  return mode === undefined
    ? rows
    : rows.filter((row) => (row.modes ?? []).some((rowMode) => rowMode.id === mode))
}
