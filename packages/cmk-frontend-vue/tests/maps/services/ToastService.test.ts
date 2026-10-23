/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastService } from '@/maps/services/ToastService'

let toasts: ToastService

beforeEach(() => {
  vi.useFakeTimers()
  toasts = new ToastService()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('ToastService', () => {
  it('shows what an action did, with its kind', () => {
    toasts.success(untranslated('Saved'))
    expect(toasts.toasts.value).toMatchObject([{ type: 'success', message: 'Saved' }])
  })

  it('keeps several messages apart', () => {
    toasts.success(untranslated('one'))
    toasts.error(untranslated('two'))
    expect(toasts.toasts.value.map((toast) => toast.id)).toEqual([0, 1])
  })

  it('carries an offered follow-up action', () => {
    const onClick = vi.fn()
    toasts.success(untranslated('Deleted'), { label: untranslated('Undo'), onClick })
    toasts.toasts.value[0]?.action?.onClick()
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('dismisses a confirmation on its own', () => {
    toasts.success(untranslated('Saved'))
    vi.advanceTimersByTime(3500)
    expect(toasts.toasts.value).toEqual([])
  })

  it('leaves a problem up longer than a confirmation', () => {
    toasts.error(untranslated('Failed'))
    vi.advanceTimersByTime(3500)
    expect(toasts.toasts.value).toHaveLength(1)
    vi.advanceTimersByTime(1500)
    expect(toasts.toasts.value).toEqual([])
  })

  it('dismisses the message whose time is up, not whichever is first', () => {
    toasts.error(untranslated('Failed'))
    vi.advanceTimersByTime(1000)
    toasts.success(untranslated('Saved'))
    vi.advanceTimersByTime(3500)
    expect(toasts.toasts.value.map((toast) => toast.message)).toEqual(['Failed'])
  })

  it('drops pending timers with the app, so none fires into a torn-down view', () => {
    toasts.success(untranslated('Saved'))
    toasts.dispose()
    expect(toasts.toasts.value).toEqual([])
    expect(vi.getTimerCount()).toBe(0)
  })
})
