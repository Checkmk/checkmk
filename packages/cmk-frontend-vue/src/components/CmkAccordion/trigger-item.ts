/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { inject, type InjectionKey } from 'vue'

export const triggerItemKey = Symbol() as InjectionKey<(id: string) => void>

export function getInjectedTriggerItem(): (id: string) => void {
  const triggerItem = inject(triggerItemKey)
  if (triggerItem === undefined) {
    throw Error('can only be used inside accordion context')
  }
  return triggerItem
}
