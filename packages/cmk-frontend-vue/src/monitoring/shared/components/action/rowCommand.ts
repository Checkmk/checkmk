/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onScopeDispose, ref } from 'vue'

import type { MonitoringActionRegistry } from './registry'
import { type ActionRun, prepareRun } from './run'
import type { ActionOutcome } from './types'

/** A command a row's action menu runs on the object of the row. */
export interface RowCommand<Target> {
  id: string
  target: Target
}

/**
 * The run of a command picked in a row: on that row's object alone, with the command's default
 * values. A command the registry does not know has none. Its key names the command and the object
 * it acts on, which `targetKey` tells apart: two rows may pick the same, e.g. two services the
 * host's "Check_MK" service updates.
 */
export function resolveRowCommand<Target>(
  registry: MonitoringActionRegistry<Target>,
  command: RowCommand<Target>,
  targetKey: (target: Target) => string
): ActionRun | null {
  const action = registry[command.id]
  return action
    ? { ...prepareRun(action, [command.target]), key: `${command.id}@${targetKey(command.target)}` }
    : null
}

/**
 * Run a command picked in a row on that row's object alone, with the command's default values,
 * and tell how it went. A command the registry does not know is not run, and null tells so.
 */
export async function performRowCommand<Target>(
  registry: MonitoringActionRegistry<Target>,
  command: RowCommand<Target>,
  signal?: AbortSignal
): Promise<ActionOutcome | null> {
  const action = registry[command.id]
  if (!action) {
    return null
  }
  return action.perform([command.target], action.defaultValues(), signal)
}

export interface RowCommandRunner {
  /** Whether a command picked in the row of the key still runs. */
  isBusy: (rowKey: string) => boolean
  /**
   * Run a command picked in the row of the key, the row busy until it settles. A row runs one
   * command at a time: a command picked while another still runs is not run, and null tells so.
   * The signal handed to the command aborts once the table is gone.
   */
  run: (
    rowKey: string,
    command: (signal: AbortSignal) => Promise<ActionOutcome | null>
  ) => Promise<ActionOutcome | null>
}

/** The rows of a table whose picked command still runs, as its rows show and respect it. */
export function useRowCommandRunner(): RowCommandRunner {
  const busy: Ref<ReadonlySet<string>> = ref(new Set())
  const gone = new AbortController()
  onScopeDispose(() => gone.abort())

  async function run(
    rowKey: string,
    command: (signal: AbortSignal) => Promise<ActionOutcome | null>
  ): Promise<ActionOutcome | null> {
    if (busy.value.has(rowKey)) {
      return null
    }
    busy.value = new Set(busy.value).add(rowKey)
    try {
      return await command(gone.signal)
    } finally {
      const rest = new Set(busy.value)
      rest.delete(rowKey)
      busy.value = rest
    }
  }

  return { isBusy: (rowKey) => busy.value.has(rowKey), run }
}
