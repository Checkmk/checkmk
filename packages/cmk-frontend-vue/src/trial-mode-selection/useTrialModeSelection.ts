/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type TrialModeSelectionProps } from 'cmk-shared-typing/typescript/trial_mode_selection_props'
import {
  type TrialModeSelectionRequest,
  type UnverifiedTrialReason,
  type VerificationMode
} from 'cmk-shared-typing/typescript/trial_mode_selection_request'
import { type TrialModeVerificationRequest } from 'cmk-shared-typing/typescript/trial_mode_verification_request'
import { type TrialModeVerificationResponse } from 'cmk-shared-typing/typescript/trial_mode_verification_response'
import { cmkAjax } from 'cmk-ui-library/lib/ajax'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import usei18n from 'cmk-ui-library/lib/i18n'
import { onScopeDispose, ref } from 'vue'

import { getCsrfToken } from '@/lib/csrf'

/** Seconds a resend stays unavailable after a code has been sent. */
const RESEND_COOLDOWN_SECONDS = 60

/**
 * Screens the gate dialog can show. The customer branch asks how the license is verified,
 * and "Verify later" leads to pending; the trial branch walks choice -> email -> code -> success.
 * Offline sites go choice -> unreachable -> unverified; the send limit also leads to
 * unverified.
 */
export type TrialModeScreen =
  | 'choice'
  | 'verification'
  | 'email'
  | 'code'
  | 'success'
  | 'pending'
  | 'unreachable'
  | 'unverified'

/**
 * State shared by the dialog's screens.
 *
 * A factory rather than module-scoped state: the screens are mounted once per page, and
 * a shared singleton would carry state between tests.
 */
export function useTrialModeSelection(props: TrialModeSelectionProps) {
  const { _t } = usei18n()
  const screen = ref<TrialModeScreen>('choice')
  /**
   * The address a code is sent to. Kept here rather than on the email screen now that
   * the code screen names it and the cooldown keys on it - screens are unmounted as
   * they are left, so a ref on one of them would not survive the step.
   */
  const email = ref('')
  const saving = ref(false)
  const saveFailed = ref(false)
  const emailSalt = ref('')

  /**
   * In case of an error requesting or verifying a code, contains a localised
   * error user-readable error message. Otherwise empty.
   */
  const errorMessage = ref(untranslated(''))
  /** True iff a "send code to my email" request is currently in flight. */
  const sendRequestInFlight = ref(false)

  /**
   * Seconds left before another code may be requested. Kept here rather than on the code
   * screen, so stepping back to the address and forward again does not reset it - going
   * back never consumes a send, and must not buy a fresh cooldown either.
   */
  const resendCooldown = ref(0)
  /** Address the standing cooldown belongs to. */
  const lastSentTo = ref('')
  /** When the standing cooldown runs out, as a timestamp. */
  let resendAvailableAt = 0
  let ticker: ReturnType<typeof setInterval> | undefined
  const now = ref(Date.now())
  /** Ticks `now` every second, so the limit countdown updates and resets at midnight. */
  const clock = setInterval(() => (now.value = Date.now()), 1000)
  onScopeDispose(() => clearInterval(clock))

  async function sendCodeRequest(): Promise<void> {
    cancelResendCooldown()
    sendRequestInFlight.value = true
    errorMessage.value = untranslated('')
    const request: TrialModeVerificationRequest = {
      step: 'request',
      email: email.value
    }
    try {
      const response = await cmkAjax<TrialModeVerificationResponse>(props.verification_url, {
        ...request,
        _csrf_token: getCsrfToken()
      })
      if (response.status !== 'ok' || !response.salt) {
        errorMessage.value = response.errorMessage
          ? untranslated(response.errorMessage)
          : _t('Internal error. Please try again or contact Checkmk support.')
        return
      }
      emailSalt.value = response.salt
      armResendCooldown()
    } catch (e) {
      console.error('error requesting trial verification code', e)
      errorMessage.value = _t('Unable to reach Checkmk site. Please check that it is started.')
    } finally {
      sendRequestInFlight.value = false
    }
  }

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

  /**
   * Cancels the cooldown timer.
   */
  function cancelResendCooldown(): void {
    resendAvailableAt = 0
    resendCooldown.value = 0
    stopTicking()
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

  /** Offline sites get the unreachable screen. Mocked: `offline` stays unset until CMK-37828. */
  function startTrial(): void {
    goTo(props.offline ? 'unreachable' : 'email')
  }

  /**
   * Sends a code to the address and moves on to entering it.
   *
   * Re-submitting the same address while the cooldown runs leaves it alone: stepping back
   * to the address and forward again is not a new send, and must not hand out a fresh
   * cooldown - that is the one way the dialog could otherwise be used to send on demand.
   * A different address is a different rate-limit key, so it starts its own.
   */
  function sendCode(): void {
    if (sendRequestInFlight.value) {
      return
    }
    // Case-insensitive, so changing the letter case is not a new address.
    const address = email.value.toLowerCase()
    const newAddress = address !== lastSentTo.value
    lastSentTo.value = address
    if (newAddress || resendCooldown.value <= 0) {
      void sendCodeRequest()
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
    if (await persist(request)) {
      window.location.assign(target)
    }
  }

  /**
   * Records the decision; true once it is saved, false (with the error shown) if not.
   * `saving` stays set after a success, so nothing can be clicked while the page leaves.
   */
  async function persist(request: TrialModeSelectionRequest): Promise<boolean> {
    if (saving.value) {
      return false
    }
    saving.value = true
    saveFailed.value = false
    try {
      await cmkAjax(props.save_url, {
        ...request,
        _csrf_token: getCsrfToken()
      })
      return true
    } catch (e) {
      saving.value = false
      saveFailed.value = true
      console.error(e)
      return false
    }
  }

  /**
   * Saves the decision before its confirmation screen opens, so closing the tab there
   * does not bring the dialog back. "Start monitoring" then only leaves for the dashboard.
   */
  async function persistAndConfirm(
    request: TrialModeSelectionRequest,
    confirmation: TrialModeScreen
  ): Promise<void> {
    if (await persist(request)) {
      saving.value = false
      goTo(confirmation)
    }
  }

  function leaveForDashboard(): void {
    window.location.assign('index.py')
  }

  function recordTrial(): Promise<void> {
    return persistAndLeave({ selection: 'trial' }, 'index.py')
  }

  function resendCode(): void {
    void sendCodeRequest()
  }

  /** Saves the unverified trial with why the verification was skipped, then shows it. */
  function continueUnverified(reason: UnverifiedTrialReason): Promise<void> {
    return persistAndConfirm(
      { selection: 'unverified_trial', unverified_reason: reason },
      'unverified'
    )
  }

  function verifyNow(mode: VerificationMode): Promise<void> {
    return persistAndLeave(
      { selection: 'customer', verification_mode: mode },
      mode === 'online' ? props.verify_online_url : props.verify_offline_url
    )
  }

  function verifyLater(): Promise<void> {
    return persistAndConfirm({ selection: 'customer' }, 'pending')
  }

  return {
    screen,
    email,
    saving,
    saveFailed,
    resendCooldown,
    sendRequestInFlight,
    errorMessage,
    startTrial,
    continueUnverified,
    sendCode,
    resendCode,
    goTo,
    recordTrial,
    leaveForDashboard,
    verifyNow,
    verifyLater
  }
}
