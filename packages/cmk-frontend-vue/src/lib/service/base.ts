/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable @typescript-eslint/no-explicit-any */
import { ref } from 'vue'

import {
  type KeyShortcut,
  type KeyShortcutHandlerCallback,
  type KeyShortcutService
} from '@/lib/keyShortcuts'
import { randomId } from '@/lib/randomId'

const callbacks: {
  [key: string]: { id: string; cb: (...args: any) => void }[]
} = {}

export class ServiceBase {
  protected shortCutEventIds = ref<string[]>([])
  protected shortCutsRegistered: {
    shortcut: KeyShortcut
    cb: KeyShortcutHandlerCallback
  }[] = []

  public constructor(
    protected serviceId: string,
    protected shortCutService: KeyShortcutService
  ) {}

  public registerShortCut(shortcut: KeyShortcut, cb: KeyShortcutHandlerCallback) {
    this.shortCutsRegistered.push({ shortcut, cb })
  }

  public enableShortCuts() {
    for (const sc of this.shortCutsRegistered) {
      this.shortCutEventIds.value.push(this.shortCutService.on(sc.shortcut, sc.cb))
    }
  }

  public disableShortCuts() {
    this.shortCutService.remove(this.shortCutEventIds.value)
    this.shortCutEventIds.value = []
  }

  protected pushCallBack(key: string, cb: (...args: any) => void) {
    const ensuredKey = this.ensureKey(key)
    const id = randomId()
    callbacks[ensuredKey]?.push({ id, cb })
    return id
  }

  protected dispatchCallback(key: string, ...args: any) {
    const ensuredKey = this.ensureKey(key)
    callbacks[ensuredKey]?.forEach((c) => {
      c.cb(...args)
    })
  }

  private ensureKey(key: string) {
    const ensuredKey = `${this.serviceId}-${key}`
    if (!callbacks[ensuredKey]) {
      callbacks[ensuredKey] = []
    }

    return ensuredKey
  }
}
