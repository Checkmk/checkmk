/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { type Ref, nextTick, ref, shallowRef } from 'vue'

import { useDateTimeDraft } from '@/components/date-time/useDateTimeDraft'

type DateValue = CalendarDate | null
type SaveHandler = () => boolean | Promise<boolean>

// The fixed date used as the default staged value; its exact value is arbitrary.
const INITIAL_DATE = new CalendarDate(2026, 3, 9)

// A trigger field (`currentTarget`) holding one segment, plus an unrelated outside control.
const buildTriggerField = () => {
  const field = document.createElement('div')
  const segment = document.createElement('input')
  field.appendChild(segment)
  const outside = document.createElement('button')
  return { field, segment, outside }
}

const focusOut = (field: HTMLElement, relatedTarget: EventTarget | null): FocusEvent =>
  ({ relatedTarget, currentTarget: field }) as unknown as FocusEvent

const setup = (options?: {
  open?: boolean
  initial?: DateValue
  commitResult?: boolean | void
  canApply?: (() => boolean) | undefined
  save?:
    | {
        mode: () => boolean
        checked: Ref<boolean>
        handler: () => SaveHandler | undefined
      }
    | undefined
}) => {
  const open = ref(options?.open ?? false)
  const model = shallowRef<DateValue>(options?.initial ?? INITIAL_DATE)
  const commit = vi.fn((value: DateValue): boolean | void => {
    if (options?.commitResult === false) {
      return false
    }
    model.value = value
    return options?.commitResult
  })
  const { draft, pendingSave, confirm, onTriggerFocusOut } = useDateTimeDraft<DateValue>({
    open,
    source: () => model.value,
    clone: (value) => value,
    commit,
    canApply: options?.canApply,
    save: options?.save
  })
  return { open, model, commit, draft, pendingSave, confirm, onTriggerFocusOut }
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useDateTimeDraft — staging', () => {
  test('init clones source', () => {
    const { draft, model } = setup()
    expect(draft.value).toBe(model.value)
    expect(draft.value?.toString()).toBe(INITIAL_DATE.toString())
  })

  test('mirror while closed', async () => {
    const { draft, model } = setup()
    model.value = new CalendarDate(2026, 4, 1)
    await nextTick()
    expect(draft.value?.toString()).toBe('2026-04-01')
  })

  test('detached while open', async () => {
    const { open, draft, model } = setup()
    open.value = true
    await nextTick()
    model.value = new CalendarDate(2026, 4, 1)
    await nextTick()
    expect(draft.value?.toString()).toBe(INITIAL_DATE.toString())
  })

  test('revert on close', async () => {
    const { open, draft } = setup()
    open.value = true
    await nextTick()
    draft.value = new CalendarDate(2026, 12, 25)
    open.value = false
    await nextTick()
    expect(draft.value?.toString()).toBe(INITIAL_DATE.toString())
  })

  test('confirm commits the draft and closes on success', async () => {
    const { open, draft, confirm, model } = setup({ open: true, commitResult: true })
    draft.value = new CalendarDate(2026, 12, 25)
    await confirm()
    expect(open.value).toBe(false)
    expect(model.value?.toString()).toBe('2026-12-25')
  })

  test('confirm commits when commit returns undefined', async () => {
    const { open, draft, confirm, model } = setup({ open: true, commitResult: undefined })
    draft.value = new CalendarDate(2026, 12, 25)
    await confirm()
    expect(open.value).toBe(false)
    expect(model.value?.toString()).toBe('2026-12-25')
  })

  test('confirm stays open when commit rejects', async () => {
    const { open, draft, confirm, model } = setup({ open: true, commitResult: false })
    draft.value = new CalendarDate(2026, 12, 25)
    await confirm()
    expect(open.value).toBe(true)
    expect(model.value?.toString()).toBe(INITIAL_DATE.toString())
  })

  test('confirm is a no-op when canApply is false', async () => {
    const { open, draft, confirm, commit, model } = setup({
      open: true,
      commitResult: true,
      canApply: () => false
    })
    draft.value = new CalendarDate(2026, 12, 25)
    await confirm()
    expect(commit).not.toHaveBeenCalled()
    expect(open.value).toBe(true)
    expect(model.value?.toString()).toBe(INITIAL_DATE.toString())
  })
})

describe('useDateTimeDraft.confirm — save mode', () => {
  // Drive confirm() through the save gating: open flyout, a committable draft, and a Save checkbox
  // that is ticked + save mode on by default (the cases override `checked`/`mode` as needed).
  const saveSetup = (
    handler: SaveHandler,
    overrides?: { checked?: boolean; mode?: boolean; canApply?: () => boolean }
  ) => {
    const checked = ref(overrides?.checked ?? true)
    return setup({
      open: true,
      commitResult: true,
      canApply: overrides?.canApply,
      save: { mode: () => overrides?.mode ?? true, checked, handler: () => handler }
    })
  }

  test('awaits a ticked handler that resolves true, then commits and closes', async () => {
    let resolveHandler: (ok: boolean) => void = () => {}
    const handler = vi.fn(
      () =>
        new Promise<boolean>((resolve) => {
          resolveHandler = resolve
        })
    )
    const { open, draft, confirm, commit, model } = saveSetup(handler)
    draft.value = new CalendarDate(2026, 12, 25)

    const pending = confirm()
    expect(handler).toHaveBeenCalledOnce()
    // Nothing commits or closes until the handler resolves.
    expect(commit).not.toHaveBeenCalled()
    expect(open.value).toBe(true)

    resolveHandler(true)
    await pending
    expect(commit).toHaveBeenCalledOnce()
    expect(open.value).toBe(false)
    expect(model.value?.toString()).toBe('2026-12-25')
  })

  test('a handler resolving false aborts: no commit, stays open', async () => {
    const handler = vi.fn(() => false)
    const { open, draft, confirm, commit } = saveSetup(handler)
    draft.value = new CalendarDate(2026, 12, 25)
    await confirm()
    expect(commit).not.toHaveBeenCalled()
    expect(open.value).toBe(true)
  })

  test('a rejecting handler aborts and swallows the exception', async () => {
    const handler = vi.fn(() => Promise.reject(new Error('save failed')))
    const { open, draft, confirm, commit } = saveSetup(handler)
    draft.value = new CalendarDate(2026, 12, 25)
    await expect(confirm()).resolves.toBeUndefined()
    expect(handler).toHaveBeenCalledOnce()
    expect(commit).not.toHaveBeenCalled()
    expect(open.value).toBe(true)
  })

  test('an unticked Save checkbox skips the handler but still commits and closes', async () => {
    const handler = vi.fn(() => true)
    const { open, draft, confirm, commit } = saveSetup(handler, { checked: false })
    draft.value = new CalendarDate(2026, 12, 25)
    await confirm()
    expect(handler).not.toHaveBeenCalled()
    expect(commit).toHaveBeenCalledOnce()
    expect(open.value).toBe(false)
  })

  test('save mode off skips the handler', async () => {
    const handler = vi.fn(() => true)
    const { confirm, commit } = saveSetup(handler, { mode: false })
    await confirm()
    expect(handler).not.toHaveBeenCalled()
    expect(commit).toHaveBeenCalledOnce()
  })

  test('the canApply guard runs before the save handler', async () => {
    const handler = vi.fn(() => true)
    const { confirm, commit } = saveSetup(handler, { canApply: () => false })
    await confirm()
    expect(handler).not.toHaveBeenCalled()
    expect(commit).not.toHaveBeenCalled()
  })

  test('pending is true while the handler is in flight and false once it settles', async () => {
    let resolveHandler: (ok: boolean) => void = () => {}
    const handler = vi.fn(
      () =>
        new Promise<boolean>((resolve) => {
          resolveHandler = resolve
        })
    )
    const { confirm, pendingSave } = saveSetup(handler)
    expect(pendingSave.value).toBe(false)

    const settled = confirm()
    expect(pendingSave.value).toBe(true)

    resolveHandler(true)
    await settled
    expect(pendingSave.value).toBe(false)
  })

  test('pending resets to false after a rejecting handler', async () => {
    const handler = vi.fn(() => Promise.reject(new Error('save failed')))
    const { confirm, pendingSave } = saveSetup(handler)
    await confirm()
    expect(pendingSave.value).toBe(false)
  })

  test('a second confirm while one is pending is a no-op (no concurrent save)', async () => {
    let resolveHandler: (ok: boolean) => void = () => {}
    const handler = vi.fn(
      () =>
        new Promise<boolean>((resolve) => {
          resolveHandler = resolve
        })
    )
    const { open, draft, confirm, commit, model } = saveSetup(handler)
    draft.value = new CalendarDate(2026, 12, 25)

    const first = confirm()
    // Re-entry while the first save is still awaiting: ignored, handler not called again.
    await confirm()
    expect(handler).toHaveBeenCalledOnce()
    expect(commit).not.toHaveBeenCalled()
    expect(open.value).toBe(true)

    resolveHandler(true)
    await first
    expect(handler).toHaveBeenCalledOnce()
    expect(commit).toHaveBeenCalledOnce()
    expect(open.value).toBe(false)
    expect(model.value?.toString()).toBe('2026-12-25')
  })
})

describe('useDateTimeDraft.onTriggerFocusOut', () => {
  test('focusout while open → no-op', () => {
    const { open, draft, onTriggerFocusOut } = setup()
    const { field, outside } = buildTriggerField()
    open.value = true
    draft.value = new CalendarDate(2026, 12, 25)
    onTriggerFocusOut(focusOut(field, outside))
    expect(draft.value.toString()).toBe('2026-12-25')
  })

  test('focusout intra-field → no-op', () => {
    const { draft, onTriggerFocusOut } = setup()
    const { field, segment } = buildTriggerField()
    draft.value = new CalendarDate(2026, 12, 25)
    onTriggerFocusOut(focusOut(field, segment))
    expect(draft.value.toString()).toBe('2026-12-25')
  })

  test('focusout real leave → reset', () => {
    vi.spyOn(document, 'hasFocus').mockReturnValue(true)
    const { draft, onTriggerFocusOut } = setup()
    const { field, outside } = buildTriggerField()
    draft.value = new CalendarDate(2026, 12, 25)
    onTriggerFocusOut(focusOut(field, outside))
    expect(draft.value?.toString()).toBe(INITIAL_DATE.toString())
  })
})
