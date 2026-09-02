/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type Ref, ref } from 'vue'

export type ToastType = 'success' | 'error' | 'warning'

export interface ToastAction {
  label: TranslatedString
  onClick: () => void
}

export interface Toast {
  id: number
  type: ToastType
  message: TranslatedString
  action?: ToastAction
}

const SUCCESS_DURATION_MS = 3500
const PROBLEM_DURATION_MS = 5000

/**
 * The SPA's transient feedback channel: what an action did, or why it did not.
 *
 * Rendered by ``MapsToastContainer``, which is mounted once by ``MapsApp``. The
 * pending dismiss timers belong to the service so they go down with the app
 * instead of firing into a torn-down component.
 */
export class ToastService {
  public readonly toasts: Ref<Toast[]> = ref([])

  private nextId = 0
  private readonly timers = new Set<ReturnType<typeof setTimeout>>()

  public success(message: TranslatedString, action?: ToastAction): void {
    this.show('success', message, SUCCESS_DURATION_MS, action)
  }

  public error(message: TranslatedString): void {
    this.show('error', message, PROBLEM_DURATION_MS)
  }

  public warning(message: TranslatedString): void {
    this.show('warning', message, PROBLEM_DURATION_MS)
  }

  public dispose(): void {
    for (const timer of this.timers) {
      clearTimeout(timer)
    }
    this.timers.clear()
    this.toasts.value = []
  }

  private show(
    type: ToastType,
    message: TranslatedString,
    duration: number,
    action?: ToastAction
  ): void {
    const id = this.nextId++
    this.toasts.value.push({ id, type, message, ...(action !== undefined ? { action } : {}) })
    const timer = setTimeout(() => {
      this.timers.delete(timer)
      const index = this.toasts.value.findIndex((toast) => toast.id === id)
      if (index !== -1) {
        this.toasts.value.splice(index, 1)
      }
    }, duration)
    this.timers.add(timer)
  }
}
