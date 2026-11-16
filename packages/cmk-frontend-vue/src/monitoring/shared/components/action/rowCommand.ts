/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MonitoringActionRegistry } from './registry'
import { type ActionRun, prepareRun } from './run'

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
