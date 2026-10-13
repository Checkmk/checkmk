/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Sending one monitoring command from a modal, and what the operator sees while
 * it happens.
 *
 * A command is not idempotent -- a second acknowledgement is a second entry in
 * the audit log -- so a submit that has already won stays blocked for as long
 * as its confirmation is on screen, not just while the request is in flight.
 * The confirmation is left up briefly so the operator sees that it worked, and
 * the modal then closes itself; the pending close is dropped if the modal goes
 * away first.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type Ref, computed, onUnmounted, ref } from 'vue'

interface CommandSubmitOptions {
  /** Sends the command. Throwing is how it reports a failure. */
  send: () => Promise<void>
  /** Closes the modal, once the confirmation has been seen. */
  onDone: () => void
  /** What to say when the failure carries no message of its own. */
  fallbackError: TranslatedString
  /**
   * Turns a failure into what the operator is told. Checkmk's own message is
   * usually right, but some rejections need a hint to be actionable.
   */
  describeError?: (error: unknown) => TranslatedString
}

/** How long the confirmation stays up before the modal closes itself. */
const CONFIRMATION_MS = 1200

export interface CommandSubmit {
  /** Whether the request is in flight. */
  submitting: Ref<boolean>
  /** Whether the command went through, and its confirmation is showing. */
  succeeded: Ref<boolean>
  /** What went wrong, in the operator's words. Empty while nothing has. */
  error: Ref<TranslatedString>
  /** Whether submitting again would send a duplicate command. */
  blocked: Ref<boolean>
  submit: () => Promise<void>
  /** Refuse before sending -- a form that does not add up yet. */
  reject: (message: TranslatedString) => void
}

export function useCommandSubmit(options: CommandSubmitOptions): CommandSubmit {
  const submitting = ref(false)
  const succeeded = ref(false)
  const error = ref<TranslatedString>(untranslated(''))

  let closeTimer: number | null = null
  onUnmounted(() => {
    if (closeTimer !== null) {
      window.clearTimeout(closeTimer)
    }
  })

  const blocked = computed(() => submitting.value || succeeded.value)

  async function submit(): Promise<void> {
    if (blocked.value) {
      return
    }
    submitting.value = true
    error.value = untranslated('')
    try {
      await options.send()
      succeeded.value = true
      closeTimer = window.setTimeout(options.onDone, CONFIRMATION_MS)
    } catch (caught) {
      error.value = options.describeError
        ? options.describeError(caught)
        : caught instanceof Error
          ? untranslated(caught.message)
          : options.fallbackError
    } finally {
      submitting.value = false
    }
  }

  function reject(message: TranslatedString): void {
    error.value = message
  }

  return { submitting, succeeded, error, blocked, submit, reject }
}
