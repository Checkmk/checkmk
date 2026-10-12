/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type * as intl from '@internationalized/date'
import userEvent, { type UserEvent } from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { type TrialModeSelectionProps } from 'cmk-shared-typing/typescript/trial_mode_selection_props'
import {
  type TrialModeSelectionRequest,
  type VerificationMode
} from 'cmk-shared-typing/typescript/trial_mode_selection_request'
import { type TrialModeVerificationRequest } from 'cmk-shared-typing/typescript/trial_mode_verification_request'
import { type TrialModeVerificationResponse } from 'cmk-shared-typing/typescript/trial_mode_verification_response'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import TrialModeSelectionApp from '@/trial-mode-selection/TrialModeSelectionApp.vue'

// The success screen renders the trial end in the browser's zone. Pinning it keeps the
// expected calendar day machine-independent, and lets a test move the browser elsewhere.
const zone = vi.hoisted(() => ({ current: 'UTC' }))

vi.mock('@internationalized/date', async (importOriginal) => {
  const actual = await importOriginal<typeof intl>()
  return { ...actual, getLocalTimeZone: () => zone.current }
})

const SAVE_ENDPOINT = '*/ajax_save_trial_mode_selection.py'
const VERIFICATION_ENDPOINT = '*/ajax_send_trial_mode_request.py'

type WithCsrfToken<T> = T & { _csrf_token: string }
type SaveRequest = WithCsrfToken<TrialModeSelectionRequest>
type VerificationRequest = WithCsrfToken<TrialModeVerificationRequest>

/**
 * What the dialog sent to the site, per endpoint and in order.
 *
 * A request is recorded once it has gone through fetch, not when the dialog starts it.
 * Checks that nothing (more) was sent rely on user-event's pause after each action being
 * long enough for a request to arrive; dropping that pause (`delay: null`) would let them
 * pass without noticing a stray save.
 */
const received: { save: SaveRequest[]; verification: VerificationRequest[] } = {
  save: [],
  verification: []
}

/** The JSON body of an AJAX request, as the page handler on the site reads it. */
async function decode<T>(request: Request): Promise<T> {
  const form = new URLSearchParams(await request.text())
  return JSON.parse(form.get('request') ?? '{}') as T
}

function ajaxResult(result: unknown) {
  return HttpResponse.json({ result_code: 0, result, severity: 'success' })
}

/** Records every save before answering it. */
function onSave(answer: () => Response | Promise<Response>) {
  return http.post(SAVE_ENDPOINT, async ({ request }) => {
    received.save.push(await decode<SaveRequest>(request))
    return answer()
  })
}

/** Records every verification request before answering it. */
function onVerification(answer: (sent: VerificationRequest) => Response) {
  return http.post(VERIFICATION_ENDPOINT, async ({ request }) => {
    const sent = await decode<VerificationRequest>(request)
    received.verification.push(sent)
    return answer(sent)
  })
}

/**
 * Answers as the site does: a salt only for a sent code, and null for what its
 * response has no value for.
 */
function answerLikeTheSite(sent: VerificationRequest) {
  return ajaxResult({
    status: 'ok',
    errorMessage: null,
    salt: sent.step === 'request' ? 'fAkE_sAlT' : null
  })
}

const server = useMswServer(
  onSave(() => ajaxResult({})),
  onVerification(answerLikeTheSite)
)

/** The site rejects the save, as its page handler does for an invalid one. */
function rejectSaving() {
  // The dialog logs the failed save; that log is expected here.
  vi.spyOn(console, 'error').mockImplementation(() => {})
  server.use(onSave(() => HttpResponse.json({ result_code: 1, result: 'nope', severity: 'error' })))
}

/** The save reaches the site but never gets an answer, so it stays in flight. */
function holdSaving() {
  server.use(onSave(() => new Promise<never>(() => {})))
}

function answerVerificationWith(response: Partial<TrialModeVerificationResponse>) {
  server.use(onVerification(() => ajaxResult(response)))
}

function makeSiteUnreachableForVerification() {
  // The dialog logs the failed request; that log is expected here.
  vi.spyOn(console, 'error').mockImplementation(() => {})
  server.use(onVerification(() => HttpResponse.error()))
}

/**
 * Leaving the page. It is mocked, so the dialog stays rendered either way: whether the
 * page was left can only be read from this, not from the screen still showing.
 */
const mockLocationAssign = vi.fn()
// The page's own address: fetch resolves the relative AJAX URLs against it.
const pageHref = window.location.href

const VERIFY_ONLINE_URL = 'wato.py?mode=edit_licensing_settings&online=1'
const VERIFY_OFFLINE_URL = 'wato.py?mode=licensing_offline_verification'
const CODE_SENT = 'We sent a 6-digit code to jane.doe@example.com. It expires after 24 hours.'
const SITE_UNREACHABLE = 'Unable to reach Checkmk site. Please check that it is started.'
const SITE_ERROR = 'Simulated Failure (as returned by the backend).'
const SAVING_FAILED = 'Saving your selection failed. Please try again.'

let user: UserEvent

function renderApp(overrides: Partial<TrialModeSelectionProps> = {}) {
  return render(TrialModeSelectionApp, {
    props: {
      save_url: 'ajax_save_trial_mode_selection.py',
      verification_url: 'ajax_send_trial_mode_request.py',
      logout_url: 'logout.py',
      verify_online_url: VERIFY_ONLINE_URL,
      verify_offline_url: VERIFY_OFFLINE_URL,
      start_monitoring_url: 'view.py?view_name=allhosts',
      initial_screen: 'choice',
      user_name: 'cmkadmin',
      edition_title: 'Checkmk Ultimate',
      // 2026-08-13 12:00:00 UTC
      trial_end_timestamp: 1786622400,
      trial_length_days: 30,
      free_services_limit: 750,
      verification_domain: 'analytics.checkmk.com',
      license_verification_reprompt_hours: 168,
      unverified_trial_reprompt_hours: 48,
      ...overrides
    }
  })
}

/** A trial end that leaves 26 days, with five minutes to spare for a slow run. */
function trialEndIn26Days(): number {
  return Date.now() / 1000 + 26 * 24 * 3600 - 300
}

/** The cards are links: they navigate, just inside the dialog. */
function card(title: string): HTMLElement {
  const literalTitle = title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return screen.getByRole('link', { name: new RegExp(`^${literalTitle}`) })
}

async function startTrial() {
  await user.click(card('Start a trial'))
}

async function goToLicenseVerification() {
  await user.click(card("I'm an existing customer"))
}

function resendButton(): HTMLElement {
  return screen.getByRole('button', { name: /Resend code/ })
}

function verifyButton(): HTMLElement {
  return screen.getByRole('button', { name: 'Verify' })
}

/** Sends a code and waits for the countdown, which starts once the site has answered. */
async function reachCodeStep() {
  await startTrial()
  await user.type(screen.getByLabelText('Email address'), 'jane.doe@example.com')
  await user.click(screen.getByRole('button', { name: 'Send code' }))
  await screen.findByRole('button', { name: /^Resend code \(\d:\d\d\)$/ })
}

/*
 * Asks for a code to the address, and the send fails: the site answers that no code went
 * out, as it does when analytics.checkmk.com rejects the send or cannot be reached.
 * A verify is still answered like the site does.
 */
async function failCodeSendTo(address: string) {
  server.use(
    onVerification((sent) =>
      sent.step === 'request'
        ? ajaxResult({ status: 'error', errorMessage: SITE_ERROR })
        : answerLikeTheSite(sent)
    )
  )
  await user.type(screen.getByLabelText('Email address'), `${address}{Enter}`)
  await screen.findByText(SITE_ERROR)
}

function codeDigits(): HTMLElement[] {
  return screen.getAllByRole('textbox', { name: /^Digit \d of 6$/ })
}

/** Fills the last box first, so the code ends up complete without ever auto-submitting. */
async function typeCodeOutOfOrder() {
  const digits = codeDigits()
  await user.type(digits[5]!, '2')
  for (const [index, digit] of ['4', '2', '4', '2', '4'].entries()) {
    await user.type(digits[index]!, digit)
  }
}

function customerSelection(verificationMode?: VerificationMode): SaveRequest {
  return {
    selection: 'customer',
    ...(verificationMode ? { verification_mode: verificationMode } : {}),
    _csrf_token: 'the-csrf-token'
  }
}

function reportErrorForVerification() {
  answerVerificationWith({ status: 'error', errorMessage: SITE_ERROR })
}

describe('TrialModeSelectionApp', () => {
  beforeEach(() => {
    user = userEvent.setup()
    zone.current = 'UTC'
    // Without this the long date below follows the machine's locale - 'August 13, 2026'
    // on one agent, '13 August 2026' on the next. The zone is pinned separately, above.
    vi.spyOn(navigator, 'language', 'get').mockReturnValue('en-US')
    received.save = []
    received.verification = []
    mockLocationAssign.mockClear()
    document.head.innerHTML = '<meta name="cmk-csrf-token" content="the-csrf-token">'
    Object.defineProperty(window, 'location', {
      value: { href: pageHref, assign: mockLocationAssign },
      writable: true
    })
  })

  it('renders the heading and both options', () => {
    renderApp()

    expect(screen.getByText('Welcome to your new Checkmk site')).toBeInTheDocument()
    expect(card('Start a trial')).toBeInTheDocument()
    expect(card("I'm an existing customer")).toBeInTheDocument()
  })

  it('offers logging out', () => {
    renderApp()

    expect(screen.getByText(/Signed in as cmkadmin/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Log out' })).toHaveAttribute('href', 'logout.py')
  })

  it('opens the trial branch without recording anything yet', async () => {
    renderApp()

    await startTrial()

    // The decision is only saved at the end of the branch, so an abandoned dialog
    // reappears on the next admin login instead of quietly opening the gate.
    expect(screen.getByText('Verify your email address')).toBeInTheDocument()
    expect(received.save).toEqual([])
    expect(mockLocationAssign).not.toHaveBeenCalled()
  })

  it('moves the focus to the heading of the screen it opens', async () => {
    renderApp()

    await goToLicenseVerification()

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Verify your license' })).toHaveFocus()
    })
  })

  it('gives the focus back to the trial card on Back', async () => {
    renderApp()
    await goToLicenseVerification()

    await user.click(screen.getByRole('button', { name: 'Back' }))

    await waitFor(() => {
      expect(card('Start a trial')).toHaveFocus()
    })
  })

  describe('license verification step', () => {
    it('opens straight on the step when the page asks for it', () => {
      renderApp({ initial_screen: 'verification' })

      expect(screen.getByRole('heading', { name: 'Verify your license' })).toBeInTheDocument()
      expect(screen.queryByText('Start a trial')).not.toBeInTheDocument()
    })

    it('replaces the entry choice instead of adding to it', async () => {
      renderApp()

      await goToLicenseVerification()

      expect(
        screen.getByText('Choose how to validate the license for this site.')
      ).toBeInTheDocument()
      expect(card('Verify online')).toBeInTheDocument()
      expect(card('Verify offline')).toBeInTheDocument()
      expect(screen.queryByText('Welcome to your new Checkmk site')).not.toBeInTheDocument()
      expect(screen.queryByText('Start a trial')).not.toBeInTheDocument()
    })

    it('does not persist the selection yet', async () => {
      renderApp()

      await goToLicenseVerification()

      expect(received.save).toEqual([])
      expect(mockLocationAssign).not.toHaveBeenCalled()
    })

    // prettier-ignore
    it.each([
      { title: 'Verify online',  mode: 'online',  target: VERIFY_ONLINE_URL },
      { title: 'Verify offline', mode: 'offline', target: VERIFY_OFFLINE_URL }
    ] as const)('persists the selection and opens the $mode verification on $title', async ({ title, mode, target }) => {
      renderApp()
      await goToLicenseVerification()

      await user.click(card(title))

      await waitFor(() => {
        expect(received.save).toEqual([customerSelection(mode)])
        expect(mockLocationAssign).toHaveBeenCalledWith(target)
      })
    })

    it('saves the customer selection and shows the pending activation on "Verify later"', async () => {
      renderApp()
      await goToLicenseVerification()

      await user.click(screen.getByRole('button', { name: 'Verify later' }))

      expect(
        await screen.findByRole('heading', { name: 'License activation pending' })
      ).toBeInTheDocument()
      expect(received.save).toEqual([customerSelection()])
      expect(mockLocationAssign).not.toHaveBeenCalled()
    })

    it('shows the days left of the trial while the license activation is pending', async () => {
      renderApp({ trial_end_timestamp: trialEndIn26Days() })
      await goToLicenseVerification()

      await user.click(screen.getByRole('button', { name: 'Verify later' }))

      expect(await screen.findByText('Full features · 26 days left')).toBeInTheDocument()
    })

    it('leaves for the page it was given on "Start monitoring" without saving again', async () => {
      renderApp()
      await goToLicenseVerification()
      await user.click(screen.getByRole('button', { name: 'Verify later' }))
      await screen.findByRole('heading', { name: 'License activation pending' })

      await user.click(screen.getByRole('button', { name: 'Start monitoring' }))

      expect(mockLocationAssign).toHaveBeenCalledWith('view.py?view_name=allhosts')
      expect(received.save).toHaveLength(1)
    })

    it('names the reminder interval of the pending activation', async () => {
      renderApp()
      await goToLicenseVerification()

      await user.click(screen.getByRole('button', { name: 'Verify later' }))

      expect(await screen.findByText(/We'll remind you every 7 days\./)).toBeInTheDocument()
    })

    it('offers no way back once the license activation is pending', async () => {
      renderApp()
      await goToLicenseVerification()
      await user.click(screen.getByRole('button', { name: 'Verify later' }))
      await screen.findByRole('heading', { name: 'License activation pending' })

      expect(screen.queryByRole('button', { name: 'Back' })).not.toBeInTheDocument()
    })

    it('stays on the step and shows an error when saving "Verify later" fails', async () => {
      renderApp()
      await goToLicenseVerification()
      rejectSaving()

      await user.click(screen.getByRole('button', { name: 'Verify later' }))

      expect(await screen.findByText(SAVING_FAILED)).toBeInTheDocument()
      expect(screen.getByText('Verify your license')).toBeInTheDocument()
    })

    it('returns to the undecided entry choice on "Back"', async () => {
      renderApp()
      await goToLicenseVerification()

      await user.click(screen.getByRole('button', { name: 'Back' }))

      expect(screen.getByText('Welcome to your new Checkmk site')).toBeInTheDocument()
      expect(screen.queryByText('Verify online')).not.toBeInTheDocument()
      expect(received.save).toEqual([])
    })

    it('blocks its buttons while a verification is still being saved', async () => {
      holdSaving()
      renderApp()
      await goToLicenseVerification()

      await user.click(card('Verify online'))
      await waitFor(() => {
        expect(received.save).toHaveLength(1)
      })

      expect(screen.getByRole('button', { name: 'Back' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'Verify later' })).toBeDisabled()
    })

    // The cards are not buttons: `disabled` only dims them, and keyboard activation
    // still reaches the callback. The guard on the save is what stops a second one.
    it('ignores a second verification while the first is still being saved', async () => {
      holdSaving()
      renderApp()
      await goToLicenseVerification()
      await user.click(card('Verify online'))
      await waitFor(() => {
        expect(received.save).toHaveLength(1)
      })

      await user.click(card('Verify offline'))

      expect(received.save).toEqual([customerSelection('online')])
    })

    it('keeps the user on the step and shows an error when saving fails', async () => {
      renderApp()
      await goToLicenseVerification()
      rejectSaving()

      await user.click(card('Verify online'))

      expect(await screen.findByText(SAVING_FAILED)).toBeInTheDocument()
      expect(card('Verify offline')).toBeInTheDocument()
      expect(mockLocationAssign).not.toHaveBeenCalled()
    })
  })

  describe('offline site', () => {
    async function continueOffline() {
      await startTrial()
      await user.click(screen.getByRole('button', { name: 'Continue as offline trial' }))
    }

    it('explains the blocked connection instead of asking for an email address', async () => {
      renderApp({ offline: true })

      await startTrial()

      expect(
        screen.getByRole('heading', { name: /This site can't reach analytics.checkmk.com/ })
      ).toBeInTheDocument()
      expect(screen.queryByLabelText('Email address')).not.toBeInTheDocument()
    })

    it('names the domain the page was given', async () => {
      renderApp({ offline: true, verification_domain: 'mock.example.com' })

      await startTrial()

      expect(
        screen.getByRole('heading', { name: /This site can't reach mock.example.com/ })
      ).toBeInTheDocument()
    })

    it('returns to the undecided entry choice on Back', async () => {
      renderApp({ offline: true })
      await startTrial()

      await user.click(screen.getByRole('button', { name: 'Back' }))

      expect(screen.getByText('Welcome to your new Checkmk site')).toBeInTheDocument()
      expect(received.save).toEqual([])
    })

    it('names the reminder interval of the unverified trial', async () => {
      renderApp({ offline: true })

      await continueOffline()

      expect(await screen.findByText(/at most once every 48 hours/)).toBeInTheDocument()
    })

    it('saves the unverified trial and shows it on Continue as offline trial', async () => {
      renderApp({ offline: true })

      await continueOffline()

      expect(await screen.findByRole('heading', { name: 'Unverified trial' })).toBeInTheDocument()
      expect(received.save).toEqual([
        {
          selection: 'unverified_trial',
          unverified_reason: 'offline',
          _csrf_token: 'the-csrf-token'
        } satisfies SaveRequest
      ])
      expect(mockLocationAssign).not.toHaveBeenCalled()
    })

    it('shows the days left of the unverified trial', async () => {
      renderApp({ offline: true, trial_end_timestamp: trialEndIn26Days() })

      await continueOffline()

      expect(await screen.findByText('Full features · 26 days left')).toBeInTheDocument()
    })

    it('shows no days left once the trial has ended', async () => {
      renderApp({ offline: true, trial_end_timestamp: Date.now() / 1000 - 2 * 24 * 3600 })

      await continueOffline()

      expect(await screen.findByRole('heading', { name: 'Unverified trial' })).toBeInTheDocument()
      expect(screen.queryByText(/days? left/)).not.toBeInTheDocument()
    })

    it('shows at most the trial length as days left', async () => {
      renderApp({ offline: true, trial_end_timestamp: Date.now() / 1000 + 33 * 24 * 3600 })

      await continueOffline()

      expect(await screen.findByText('Full features · 30 days left')).toBeInTheDocument()
    })

    it('offers no way back once the unverified trial is saved', async () => {
      renderApp({ offline: true })
      await continueOffline()
      await screen.findByRole('heading', { name: 'Unverified trial' })

      expect(screen.queryByRole('button', { name: 'Back' })).not.toBeInTheDocument()
    })

    it('leaves for the page it was given on Start monitoring without saving again', async () => {
      renderApp({ offline: true })
      await continueOffline()
      await screen.findByRole('heading', { name: 'Unverified trial' })

      await user.click(screen.getByRole('button', { name: 'Start monitoring' }))

      expect(mockLocationAssign).toHaveBeenCalledWith('view.py?view_name=allhosts')
      expect(received.save).toHaveLength(1)
    })

    it('blocks its buttons while the offline trial is still being saved', async () => {
      holdSaving()
      renderApp({ offline: true })

      await continueOffline()
      await waitFor(() => {
        expect(received.save).toHaveLength(1)
      })

      expect(screen.getByRole('button', { name: 'Back' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'Retry' })).toBeDisabled()
    })

    it('stays on the blocked connection and shows an error when saving fails', async () => {
      renderApp({ offline: true })
      rejectSaving()

      await continueOffline()

      expect(await screen.findByText(SAVING_FAILED)).toBeInTheDocument()
      expect(
        screen.getByRole('heading', { name: /This site can't reach analytics.checkmk.com/ })
      ).toBeInTheDocument()
    })

    it('asks for an email address when the page does not say the site is offline', async () => {
      // The props type has no null, so the whole object is cast.
      renderApp({ offline: null } as unknown as Partial<TrialModeSelectionProps>)

      await startTrial()

      expect(screen.getByText('Verify your email address')).toBeInTheDocument()
    })
  })

  describe('email step', () => {
    it('returns to the entry choice on Back', async () => {
      renderApp()
      await startTrial()

      await user.click(screen.getByRole('button', { name: 'Back' }))

      expect(screen.getByText('Welcome to your new Checkmk site')).toBeInTheDocument()
      expect(received.save).toEqual([])
    })

    it('rejects a malformed address instead of advancing', async () => {
      renderApp()
      await startTrial()

      await user.type(screen.getByLabelText('Email address'), 'jane.doe@example')
      await user.click(screen.getByRole('button', { name: 'Send code' }))

      expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument()
      expect(screen.getByText('Verify your email address')).toBeInTheDocument()
    })

    it('clears the complaint as soon as the address is edited again', async () => {
      renderApp()
      await startTrial()

      await user.click(screen.getByRole('button', { name: 'Send code' }))
      expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument()

      await user.type(screen.getByLabelText('Email address'), 'j')

      expect(screen.queryByText('Enter a valid email address.')).not.toBeInTheDocument()
    })

    it('moves on to the code on Enter after a well-formed address', async () => {
      renderApp()
      await startTrial()

      await user.type(screen.getByLabelText('Email address'), 'jane.doe@example.com{Enter}')

      expect(screen.getByText('Enter your verification code')).toBeInTheDocument()
    })

    it('requests a code for the address entered', async () => {
      renderApp()
      await startTrial()

      await user.type(screen.getByLabelText('Email address'), 'jane.doe@example.com{Enter}')

      await waitFor(() => {
        expect(received.verification).toEqual([
          {
            step: 'request',
            email: 'jane.doe@example.com',
            _csrf_token: 'the-csrf-token'
          } satisfies VerificationRequest
        ])
      })
    })

    it('sends the code to the address without the whitespace around it', async () => {
      renderApp()
      await startTrial()

      await user.type(screen.getByLabelText('Email address'), '  jane.doe@example.com  ')
      await user.click(screen.getByRole('button', { name: 'Send code' }))

      await waitFor(() => {
        expect(received.verification).toEqual([
          {
            step: 'request',
            email: 'jane.doe@example.com',
            _csrf_token: 'the-csrf-token'
          } satisfies VerificationRequest
        ])
      })
    })

    it('leaves the newsletter opt-in off', async () => {
      renderApp()

      await startTrial()

      expect(screen.getByRole('checkbox', { name: /email newsletters/ })).not.toBeChecked()
    })

    it('does not opt in to the newsletter from the unsubscribe link in its label', async () => {
      renderApp()
      await startTrial()

      // The legal notice below carries an unsubscribe link of its own; this is the one
      // inside the checkbox's label, where a plain click would activate the control as
      // its default action.
      await user.click(
        screen.getByRole('link', { name: 'unsubscribe from the newsletter by email' })
      )

      expect(screen.getByRole('checkbox', { name: /email newsletters/ })).not.toBeChecked()
    })

    // prettier-ignore
    describe.each([
      { failure: 'the site cannot be reached', failCodeRequest: makeSiteUnreachableForVerification, reason: SITE_UNREACHABLE },
      { failure: 'the site reports an error',  failCodeRequest: reportErrorForVerification,         reason: SITE_ERROR }
    ])('when $failure', ({ failCodeRequest, reason }) => {
      async function requestCode() {
        failCodeRequest()
        renderApp()
        await startTrial()
        await user.type(screen.getByLabelText('Email address'), 'jane.doe@example.com{Enter}')
      }

      it('says why no code was sent', async () => {
        await requestCode()

        expect(await screen.findByText(reason)).toBeInTheDocument()
      })

      it('offers a resend straight away', async () => {
        await requestCode()
        await screen.findByText(reason)

        expect(resendButton()).toBeEnabled()
      })

      it('does not claim that a code was sent', async () => {
        await requestCode()
        await screen.findByText(reason)

        expect(screen.queryByText(CODE_SENT)).not.toBeInTheDocument()
      })
    })
  })

  describe('code step', () => {
    it('names the address the code went to', async () => {
      renderApp()

      await reachCodeStep()

      expect(screen.getByText(CODE_SENT)).toBeInTheDocument()
    })

    it('advances on the sixth digit without a click on Verify', async () => {
      renderApp()
      await reachCodeStep()

      await user.type(codeDigits()[0]!, '424242')

      expect(await screen.findByText('Trial verified')).toBeInTheDocument()
    })

    it('keeps Verify out of reach until the code is complete', async () => {
      renderApp()
      await reachCodeStep()

      expect(verifyButton()).toBeDisabled()

      await user.type(codeDigits()[0]!, '42424')

      expect(verifyButton()).toBeDisabled()
    })

    // The boxes submit themselves only when the last one is the box being filled, so a
    // code finished anywhere else is what Verify and Enter are there for.
    it('waits for Verify when the code is completed out of order', async () => {
      renderApp()
      await reachCodeStep()

      await typeCodeOutOfOrder()

      expect(screen.getByText('Enter your verification code')).toBeInTheDocument()
      expect(verifyButton()).toBeEnabled()
    })

    it('verifies the code on Enter when it was completed out of order', async () => {
      renderApp()
      await reachCodeStep()
      await typeCodeOutOfOrder()

      await user.type(screen.getByRole('textbox', { name: 'Digit 6 of 6' }), '{Enter}')

      expect(await screen.findByText('Trial verified')).toBeInTheDocument()
    })

    it('sends the code back with the address and the salt it was issued with', async () => {
      renderApp()
      await reachCodeStep()

      await user.type(codeDigits()[0]!, '424242')
      await screen.findByText('Trial verified')

      expect(received.verification.at(-1)).toEqual({
        step: 'verify',
        email: 'jane.doe@example.com',
        salt: 'fAkE_sAlT',
        code: '424242',
        _csrf_token: 'the-csrf-token'
      } satisfies VerificationRequest)
    })

    it('puts the cursor in the first box, so the code can be typed straight away', async () => {
      renderApp()

      await reachCodeStep()

      await waitFor(() => {
        expect(screen.getByRole('textbox', { name: 'Digit 1 of 6' })).toHaveFocus()
      })
    })

    it('keeps the address on Back, so the code can be sent again without retyping it', async () => {
      renderApp()
      await reachCodeStep()

      await user.click(screen.getByRole('button', { name: 'Back' }))
      await user.click(screen.getByRole('button', { name: 'Send code' }))

      expect(screen.getByText(CODE_SENT)).toBeInTheDocument()
    })

    it('saves an unverified trial when the user continues without a code after an error', async () => {
      reportErrorForVerification()
      renderApp()
      await startTrial()
      await user.type(screen.getByLabelText('Email address'), 'jane.doe@example.com')
      await user.click(screen.getByRole('button', { name: 'Send code' }))

      await user.click(await screen.findByRole('button', { name: 'Continue without verification' }))

      expect(await screen.findByRole('heading', { name: 'Unverified trial' })).toBeInTheDocument()
      expect(received.save).toEqual([
        {
          selection: 'unverified_trial',
          unverified_reason: 'code_entry_error',
          _csrf_token: 'the-csrf-token'
        } satisfies SaveRequest
      ])
    })

    it('keeps the code for another try when it could not be checked', async () => {
      renderApp()
      await reachCodeStep()
      answerVerificationWith({
        status: 'error',
        errorCode: 'unavailable',
        errorMessage: 'The verification code could not be checked.'
      })

      await user.type(codeDigits()[0]!, '424242')

      expect(
        await screen.findByText('The verification code could not be checked.')
      ).toBeInTheDocument()
      expect(codeDigits().map((input) => (input as HTMLInputElement).value)).toEqual([
        '4',
        '2',
        '4',
        '2',
        '4',
        '2'
      ])
      expect(screen.getByRole('button', { name: 'Verify' })).toBeEnabled()
    })

    describe('when no code could be sent', () => {
      it('keeps Verify out of reach', async () => {
        renderApp()
        await startTrial()
        await failCodeSendTo('jane.doe@example.com')

        await typeCodeOutOfOrder()

        expect(verifyButton()).toBeDisabled()
      })

      it('does not send the code for verification on the sixth digit', async () => {
        renderApp()
        await startTrial()
        await failCodeSendTo('jane.doe@example.com')

        await user.type(codeDigits()[0]!, '424242')

        expect(received.verification.map(({ step }) => step)).toEqual(['request'])
      })

      it('verifies the code once a resend has gone through', async () => {
        renderApp()
        await startTrial()
        await failCodeSendTo('jane.doe@example.com')
        server.use(onVerification(answerLikeTheSite))
        await user.click(resendButton())
        await screen.findByRole('button', { name: /^Resend code \(\d:\d\d\)$/ })

        await user.type(codeDigits()[0]!, '424242')

        expect(await screen.findByText('Trial verified')).toBeInTheDocument()
      })

      // The salt of the code sent before belongs to the previous address.
      it('keeps Verify out of reach after a code went to another address', async () => {
        renderApp()
        await reachCodeStep()
        await user.click(screen.getByRole('button', { name: 'Back' }))
        await user.clear(screen.getByLabelText('Email address'))
        await failCodeSendTo('john.doe@example.com')

        await typeCodeOutOfOrder()

        expect(verifyButton()).toBeDisabled()
      })
    })
  })

  describe('resend cooldown', () => {
    beforeEach(() => {
      // Only the clock the countdown reads is faked. setTimeout stays real, so the
      // simulated site still answers and waitFor can poll for it.
      vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
      // Midday, so no test here crosses midnight and resets the daily send limit.
      vi.setSystemTime(Date.UTC(2026, 8, 25, 12, 0, 0))
      // Handing user-event the fake clock rather than letting real elapsed time drive it:
      // the countdown then only moves where a test advances it, which is what makes the
      // exact seconds below exact rather than a race against how loaded the machine is.
      user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    /** Resends once the cooldown is over, and waits for the site to confirm the new code. */
    async function resend() {
      await vi.advanceTimersByTimeAsync(60_000)
      await user.click(resendButton())
      await screen.findByRole('button', { name: 'Resend code (1:00)' })
    }

    it('starts counting down from the first send, not from the first resend', async () => {
      renderApp()
      await reachCodeStep()

      expect(resendButton()).toHaveTextContent('Resend code (1:00)')
      expect(resendButton()).toBeDisabled()

      await vi.advanceTimersByTimeAsync(13_000)

      expect(resendButton()).toHaveTextContent('Resend code (0:47)')
    })

    it('re-enables the button when the countdown reaches zero', async () => {
      renderApp()
      await reachCodeStep()

      await vi.advanceTimersByTimeAsync(60_000)

      expect(resendButton()).toHaveTextContent(/^Resend code$/)
      expect(resendButton()).toBeEnabled()
    })

    it('does not buy a fresh cooldown by stepping back and forward again', async () => {
      renderApp()
      await reachCodeStep()

      await vi.advanceTimersByTimeAsync(20_000)
      await user.click(screen.getByRole('button', { name: 'Back' }))
      await user.click(screen.getByRole('button', { name: 'Send code' }))

      // Going back never consumes a send, so it must not grant a new cooldown either.
      expect(resendButton()).toHaveTextContent('Resend code (0:40)')
    })

    it('starts a fresh cooldown for an address no code has gone to yet', async () => {
      renderApp()
      await reachCodeStep()

      await vi.advanceTimersByTimeAsync(20_000)
      await user.click(screen.getByRole('button', { name: 'Back' }))
      await user.clear(screen.getByLabelText('Email address'))
      await user.type(screen.getByLabelText('Email address'), 'john.doe@example.com')
      await user.click(screen.getByRole('button', { name: 'Send code' }))

      // A different address is a different rate-limit key, so it is owed its own cooldown.
      await waitFor(() => {
        expect(resendButton()).toHaveTextContent('Resend code (1:00)')
      })
    })

    it('holds off a resend once the service reports a limit', async () => {
      renderApp()
      answerVerificationWith({
        status: 'error',
        errorCode: 'rate_limited',
        errorMessage: 'Too many verification codes have been requested.'
      })
      await startTrial()
      await user.type(screen.getByLabelText('Email address'), 'jane.doe@example.com{Enter}')

      expect(
        await screen.findByText('Too many verification codes have been requested.')
      ).toBeInTheDocument()
      expect(resendButton()).toHaveTextContent('Resend code (1:00)')
      expect(resendButton()).toBeDisabled()
    })

    it('allows a resend right away when the code could not be sent', async () => {
      renderApp()
      await reachCodeStep()
      await vi.advanceTimersByTimeAsync(60_000)
      answerVerificationWith({
        status: 'error',
        errorCode: 'unavailable',
        errorMessage: 'The verification code could not be sent.'
      })

      await user.click(resendButton())

      expect(
        await screen.findByText('The verification code could not be sent.')
      ).toBeInTheDocument()
      expect(resendButton()).toHaveTextContent(/^Resend code$/)
      expect(resendButton()).toBeEnabled()
    })

    it('starts the cooldown over on a resend', async () => {
      renderApp()
      await reachCodeStep()

      await vi.advanceTimersByTimeAsync(60_000)
      await user.click(resendButton())

      await waitFor(() => {
        expect(resendButton()).toHaveTextContent('Resend code (1:00)')
      })
    })

    it('still verifies a code already delivered once the send limit is used up', async () => {
      renderApp()
      await reachCodeStep()
      // The first send plus four resends use up the five a day.
      for (let sends = 1; sends < 5; sends++) {
        await resend()
      }

      await user.type(codeDigits()[0]!, '424242')

      expect(await screen.findByText('Trial verified')).toBeInTheDocument()
    })

    it('empties the boxes on a resend, the previous code being dead', async () => {
      renderApp()
      await reachCodeStep()
      await typeCodeOutOfOrder()

      await resend()

      expect(verifyButton()).toBeDisabled()
    })
  })

  describe('success step', () => {
    async function verifyTrial() {
      await reachCodeStep()
      await user.type(codeDigits()[0]!, '424242')
      await screen.findByText('Trial verified')
    }

    it('names the address, the edition and the end date', async () => {
      renderApp()

      await verifyTrial()

      expect(
        screen.getByText(
          'This site is now linked to jane.doe@example.com. Your 30-day trial of Checkmk Ultimate runs until August 13, 2026 — after that, the site reverts to the free edition unless you add a license.'
        )
      ).toBeInTheDocument()
    })

    it('names the edition the page was given, not one of its own', async () => {
      renderApp({ edition_title: 'Checkmk Cloud' })

      await verifyTrial()

      expect(screen.getByText(/30-day trial of Checkmk Cloud/)).toBeInTheDocument()
    })

    // Noon UTC on the 13th is already the 14th in Auckland: the day belongs to whoever
    // is reading the dialog, not to the site.
    it('names the end date in the timezone of the browser showing it', async () => {
      zone.current = 'Pacific/Auckland'
      renderApp()

      await verifyTrial()

      expect(screen.getByText(/runs until August 14, 2026/)).toBeInTheDocument()
    })

    it('offers no way back, the branch being done', async () => {
      renderApp()

      await verifyTrial()

      expect(screen.queryByRole('button', { name: 'Back' })).not.toBeInTheDocument()
    })

    it('leaves for the dashboard on Start monitoring', async () => {
      renderApp()
      await verifyTrial()

      await user.click(screen.getByRole('button', { name: 'Start monitoring' }))

      expect(mockLocationAssign).toHaveBeenCalledWith('view.py?view_name=allhosts')
    })
  })
})
