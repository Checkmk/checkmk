/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Sending one monitoring command about many things from a modal, and what the
 * operator sees while it happens.
 *
 * The same contract as ``useCommandSubmit``, with the two differences a fan-out
 * brings. It reports how far along it is, because a wide selection takes long
 * enough that a still button would read as a hang. And it can half-succeed: if
 * some targets refused the command, the modal stays open with the count and a
 * sample of what refused, so the operator can look and try again — only a run
 * that took everywhere closes itself.
 *
 * Trying again means trying again on what refused, never on the whole
 * selection: these commands do not collapse when repeated, so re-sending to a
 * host that already took the first one would leave it with two downtimes.
 */
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type Ref, computed, onUnmounted, ref } from 'vue'

import { describeTarget, fanOutCommand } from '@/maps/map/commands/fanOutCommand'
import type { CommandTarget } from '@/maps/types/api'

/** How long the confirmation stays up before the modal closes itself. */
const CONFIRMATION_MS = 1200
/** How many of the refusals are named, before it stops being informative. */
const FAILURE_SAMPLE = 3

interface BulkCommandOptions {
  targets: () => CommandTarget[]
  /** Sends the command about one target. Throwing is how it reports failure. */
  send: (target: CommandTarget) => Promise<void>
  /** Closes the modal, once the confirmation has been seen. */
  onDone: () => void
  /** What to log a failure under. */
  what: string
}

export interface BulkCommandSubmit {
  submitting: Ref<boolean>
  /** How many targets have been dealt with, refusals included. */
  progress: Ref<number>
  /** How many took the command, across a first run and any retry of it. */
  succeeded: Ref<number>
  /** How many the next submit is about: all of them, or what refused so far. */
  pending: Ref<number>
  error: Ref<TranslatedString>
  /** Whether submitting again would send duplicates. */
  blocked: Ref<boolean>
  submit: () => Promise<void>
  reject: (message: TranslatedString) => void
}

export function useBulkCommandSubmit(options: BulkCommandOptions): BulkCommandSubmit {
  const { _t } = usei18n()
  const submitting = ref(false)
  const progress = ref(0)
  const succeeded = ref(0)
  const error = ref<TranslatedString>(untranslated(''))
  // What a run left refused, and so what trying again is about. Null until a
  // run has had the chance to narrow it.
  const refused = ref<CommandTarget[] | null>(null)
  // True between a fully successful run and the auto-close, so a second click
  // cannot send the whole fan-out again.
  const closing = ref(false)
  const pending = computed(() => (refused.value ?? options.targets()).length)

  let closeTimer: number | null = null
  onUnmounted(() => {
    if (closeTimer !== null) {
      window.clearTimeout(closeTimer)
    }
  })

  const blocked = computed(() => submitting.value || closing.value)

  async function submit(): Promise<void> {
    if (blocked.value) {
      return
    }
    submitting.value = true
    error.value = untranslated('')
    progress.value = 0
    const result = await fanOutCommand(refused.value ?? options.targets(), options.send, {
      what: options.what,
      onProgress: (done) => {
        progress.value = done
      }
    })
    // Accumulated, not replaced: after a retry the operator wants to know how
    // many of their selection took the command in the end, not how many took
    // it on this attempt.
    succeeded.value += result.succeeded
    submitting.value = false
    if (result.failed.length) {
      refused.value = result.failed
      error.value = _t('%{failed} of %{total} failed: %{sample}', {
        failed: result.failed.length,
        total: result.total,
        sample: result.failed.slice(0, FAILURE_SAMPLE).map(describeTarget).join(', ')
      })
      return
    }
    refused.value = null
    closing.value = true
    closeTimer = window.setTimeout(options.onDone, CONFIRMATION_MS)
  }

  function reject(message: TranslatedString): void {
    error.value = message
  }

  return { submitting, progress, succeeded, pending, error, blocked, submit, reject }
}
