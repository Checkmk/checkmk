/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, shallowRef, watchEffect } from 'vue'

import { focusLeftElement } from './focusLeftElement'

export interface DateTimeDraftOptions<T> {
  /** The flyout open state (the picker's `open` model). */
  open: Ref<boolean>
  /** Read the current committed value from the external model(s). Must be reactive. */
  source: () => T
  /** Copy a value so draft edits never mutate the committed source. */
  clone: (value: T) => T
  /** Write a value back to the external model(s). Called on Apply. Return `false` to reject it. */
  commit: (value: T) => boolean | void
  /** Guards `confirm`: it is a no-op when this returns `false` for the staged value (an invalid /
   *  incomplete draft). Takes the value rather than reading the draft so the picker's own
   *  `canApply` computed can reuse it without a circular type reference. When omitted the draft is
   *  always applyable and `commit`'s own return value is the only gate. */
  canApply?: ((value: T) => boolean) | undefined
  /** Save-mode gating for `confirm`. Omit for pickers without save semantics (e.g. CmkTimePicker). */
  save?:
    | {
        /** Whether the picker is in save mode at all. */
        mode: () => boolean
        /** Whether the footer's Save checkbox is ticked. */
        checked: Ref<boolean>
        /** The handler to run on "Save & apply", or `undefined` when none was provided. */
        handler: () => (() => boolean | Promise<boolean>) | undefined
      }
    | undefined
}

export interface DateTimeDraft<T> {
  /** The staged value; bound by both the trigger fields and the flyout. */
  draft: Ref<T>
  /** Whether a save handler is currently in flight. */
  pendingSave: Readonly<Ref<boolean>>
  /**
   * The single apply path: guard on `canApply`, run the save handler when save mode is engaged, then
   * commit the draft and, on success, close the flyout. Wire to every `@commit` (trigger/selector
   * Enter) and the flyout's `@apply` (footer button) so all of them behave identically.
   */
  confirm: () => Promise<void>
  /**
   * Revert a draft edited directly in the closed trigger, once focus leaves it. Bind to the trigger
   * field's `focusout`. No-op while the flyout is open (the flyout owns that case and the `open`
   * watch reverts on close), and when focus only moves between the field's own segments.
   */
  onTriggerFocusOut: (event: FocusEvent) => void
}

export function useDateTimeDraft<T>(options: DateTimeDraftOptions<T>): DateTimeDraft<T> {
  const { open, source, clone, commit, canApply, save } = options
  const draft = shallowRef<T>(clone(source())) as Ref<T>
  const pendingSave = shallowRef(false)

  watchEffect(() => {
    const current = source()
    if (!open.value) {
      // Closed: mirror the committed value (also reverts a cancelled edit). While open the draft
      // is detached and edited locally, so we leave it untouched.
      draft.value = clone(current)
    }
  })

  async function confirm(): Promise<void> {
    if (pendingSave.value) {
      return
    }
    // Don't save or close an invalid draft. This guard is what makes the Enter paths safe (the
    // footer button is already disabled in this case, but Enter has no such guard).
    if (canApply && !canApply(draft.value)) {
      return
    }
    const handler = save?.handler()
    if (save && save.mode() && save.checked.value && handler) {
      let ok: boolean
      pendingSave.value = true
      try {
        ok = await handler()
      } catch {
        // A throwing / rejecting handler behaves like a `false` response: keep the flyout open and
        // swallow the exception (the handler owns surfacing its own error to the user).
        return
      } finally {
        pendingSave.value = false
      }
      if (!ok) {
        return
      }
    }
    if (commit(draft.value) !== false) {
      open.value = false
    }
  }

  function reset(): void {
    draft.value = clone(source())
  }

  function onTriggerFocusOut(event: FocusEvent): void {
    // The flyout reverts its own open-state closes; only the closed trigger is ours to revert, and
    // only once focus actually leaves the field (not while hopping between its own segments, and
    // not on a window switch — see focusLeftElement).
    if (open.value || !focusLeftElement(event)) {
      return
    }
    reset()
  }

  return { draft, pendingSave, confirm, onTriggerFocusOut }
}
