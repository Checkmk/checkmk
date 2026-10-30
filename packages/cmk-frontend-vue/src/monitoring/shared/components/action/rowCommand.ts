/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MonitoringActionRegistry } from './registry'
import type { ActionOutcome } from './types'

/** A command a row's action menu runs on the object of the row. */
export interface RowCommand<Target> {
  id: string
  target: Target
}

/**
 * Run a command picked in a row on that row's object alone, with the command's default values,
 * and tell how it went. A command the registry does not know is not run, and null tells so.
 */
export async function performRowCommand<Target>(
  registry: MonitoringActionRegistry<Target>,
  command: RowCommand<Target>
): Promise<ActionOutcome | null> {
  const action = registry[command.id]
  if (!action) {
    return null
  }
  return action.perform([command.target], action.defaultValues())
}
