/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type TrialModeSelectionProps } from 'cmk-shared-typing/typescript/trial_mode_selection_props'
import {
  type TrialModeSelectionRequest,
  type VerificationMode
} from 'cmk-shared-typing/typescript/trial_mode_selection_request'
import { cmkAjax } from 'cmk-ui-library/lib/ajax'
import { onScopeDispose, ref } from 'vue'

import { getCsrfToken } from '@/lib/csrf'

/** Seconds a resend stays unavailable after a code has been sent. */
const RESEND_COOLDOWN_SECONDS = 60

/**
 * Screens the gate dialog can show. The customer branch is a single step, asking how the
 * license is verified; the trial branch walks choice -> email -> code -> success, and
 * the last step arrives with the rest of CMK-37568.
 */
export type TrialModeScreen = 'choice' | 'verification' | 'email' | 'code' | 'success'

/**
 * State shared by the dialog's screens.
 *
 * A factory rather than module-scoped state: the screens are mounted once per page, and
 * a shared singleton would carry state between tests.
 */
export function useTrialModeSelection(props: TrialModeSelectionProps) {
  const screen = ref<TrialModeScreen>('choice')
  /**
   * The address a code is sent to. Kept here rather than on the email screen now that
   * the code screen names it and the cooldown keys on it - screens are unmounted as
   * they are left, so a ref on one of them would not survive the step.
   */
  const email = ref('')
  const saving = ref(false)
  const saveFailed = ref(false)

  /**
   * Seconds left before another code may be requested. Kept here rather than on the code
   * screen, so stepping back to the address and forward again does not reset it - going
   * back never consumes a send, and must not buy a fresh cooldown either.
   */
  const resendCooldown = ref(0)
  /** Address the standing cooldown belongs to. */
  let lastSentTo = ''
  /** When the standing cooldown runs out, as a timestamp. */
  let resendAvailableAt = 0
  let ticker: ReturnType<typeof setInterval> | undefined

  function stopTicking(): void {
    if (ticker !== undefined) {
      clearInterval(ticker)
      ticker = undefined
    }
  }

  /**
   * Starts the cooldown over. Called whenever a code is sent, first one included.
   *
   * What counts down is the deadline, not the number of ticks: browsers clamp timers in
   * background tabs, so a counter decremented once per tick would keep the button
   * disabled well past its 60 s for anyone who switches away and comes back.
   *
   * When CMK-37828 wires the real send, the request goes out just before this: a cooldown
   * armed for a code that never left would lie about when the next one may be asked for.
   */
  function armResendCooldown(): void {
    resendAvailableAt = Date.now() + RESEND_COOLDOWN_SECONDS * 1000
    resendCooldown.value = RESEND_COOLDOWN_SECONDS
    stopTicking()
    ticker = setInterval(() => {
      resendCooldown.value = Math.max(0, Math.ceil((resendAvailableAt - Date.now()) / 1000))
      if (resendCooldown.value === 0) {
        stopTicking()
      }
    }, 1000)
  }

  onScopeDispose(stopTicking)

  function goTo(next: TrialModeScreen): void {
    // A save in flight navigates away on its own once it succeeds, so leaving the
    // screen it was started from would race it.
    if (saving.value) {
      return
    }
    saveFailed.value = false
    screen.value = next
  }

  /**
   * Sends a code to the address and moves on to entering it. Nothing actually leaves the
   * site until CMK-37828 wires this up.
   *
   * Re-submitting the same address while the cooldown runs leaves it alone: stepping back
   * to the address and forward again is not a new send, and must not hand out a fresh
   * cooldown - that is the one way the dialog could otherwise be used to send on demand.
   * A different address is a different rate-limit key, so it starts its own.
   */
  function sendCode(): void {
    if (email.value !== lastSentTo || resendCooldown.value <= 0) {
      armResendCooldown()
      lastSentTo = email.value
    }
    goTo('code')
  }

  /**
   * Records the decision for the whole site and only then leaves the gate.
   *
   * Until this runs the gate stays closed and re-prompts on the next admin login,
   * which is what makes an abandoned dialog reappear.
   */
  async function persistAndLeave(
    request: TrialModeSelectionRequest,
    target: string
  ): Promise<void> {
    if (saving.value) {
      return
    }
    saving.value = true
    saveFailed.value = false
    try {
      await cmkAjax(props.save_url, {
        ...request,
        _csrf_token: getCsrfToken()
      })
      window.location.assign(target)
    } catch (e) {
      saving.value = false
      saveFailed.value = true
      console.error(e)
    }
  }

  function verifyNow(mode: VerificationMode): Promise<void> {
    return persistAndLeave(
      { selection: 'customer', verification_mode: mode },
      mode === 'online' ? props.verify_online_url : props.verify_offline_url
    )
  }

  function verifyLater(): Promise<void> {
    return persistAndLeave({ selection: 'customer' }, 'index.py')
  }

  return {
    screen,
    email,
    saving,
    saveFailed,
    resendCooldown,
    sendCode,
    resendCode: armResendCooldown,
    goTo,
    verifyNow,
    verifyLater
  }
}
