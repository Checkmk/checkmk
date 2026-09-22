/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent, { type UserEvent } from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import TrialModeSelectionApp from '@/trial-mode-selection/TrialModeSelectionApp.vue'

const mockCmkAjax = vi.hoisted(() => vi.fn().mockResolvedValue({}))

vi.mock('cmk-ui-library/lib/ajax', () => ({
  cmkAjax: mockCmkAjax
}))

const mockLocationAssign = vi.fn()

let user: UserEvent

function renderApp() {
  return render(TrialModeSelectionApp, {
    props: {
      save_url: 'ajax_save_trial_mode_selection.py',
      logout_url: 'logout.py',
      verify_online_url: 'wato.py?mode=edit_licensing_settings&online=1',
      verify_offline_url: 'wato.py?mode=licensing_offline_verification',
      user_name: 'cmkadmin',
      edition_title: 'Checkmk Ultimate',
      // 2026-08-13 12:00:00 UTC
      trial_end_timestamp: 1786622400,
      trial_length_days: 30
    }
  })
}

async function startTrial() {
  await user.click(screen.getByText('Start a trial'))
}

async function goToLicenseVerification() {
  await user.click(screen.getByText("I'm an existing customer"))
}

async function reachCodeStep() {
  await startTrial()
  await user.type(screen.getByLabelText('Email address'), 'jane.doe@example.com')
  await user.click(screen.getByRole('button', { name: 'Send code' }))
}

function codeDigits(): HTMLInputElement[] {
  return screen.getAllByRole('textbox') as HTMLInputElement[]
}

/** Fills the last box first, so the code ends up complete without ever auto-submitting. */
async function typeCodeOutOfOrder() {
  const digits = codeDigits()
  await user.type(digits[5]!, '2')
  for (const [index, digit] of ['4', '2', '4', '2', '4'].entries()) {
    await user.type(digits[index]!, digit)
  }
}

function expectCustomerSelectionSaved(verificationMode?: 'online' | 'offline') {
  expect(mockCmkAjax).toHaveBeenCalledWith('ajax_save_trial_mode_selection.py', {
    selection: 'customer',
    ...(verificationMode ? { verification_mode: verificationMode } : {}),
    _csrf_token: 'the-csrf-token'
  })
}

describe('TrialModeSelectionApp', () => {
  beforeEach(() => {
    user = userEvent.setup()
    mockCmkAjax.mockClear()
    mockCmkAjax.mockResolvedValue({})
    mockLocationAssign.mockClear()
    document.head.innerHTML = '<meta name="cmk-csrf-token" content="the-csrf-token">'
    Object.defineProperty(window, 'location', {
      value: { assign: mockLocationAssign },
      writable: true
    })
  })

  it('renders the heading and both options', () => {
    renderApp()
    expect(screen.getByText('Welcome to your new Checkmk site')).toBeInTheDocument()
    expect(screen.getByText('Start a trial')).toBeInTheDocument()
    expect(screen.getByText("I'm an existing customer")).toBeInTheDocument()
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
    expect(mockCmkAjax).not.toHaveBeenCalled()
    expect(mockLocationAssign).not.toHaveBeenCalled()
  })

  it('moves the focus to the heading of the screen it opens', async () => {
    renderApp()
    await goToLicenseVerification()
    await waitFor(() => {
      expect(screen.getByText('Verify your license')).toHaveFocus()
    })

    await user.click(screen.getByRole('button', { name: 'Back' }))
    await waitFor(() => {
      expect(screen.getByText('Welcome to your new Checkmk site')).toHaveFocus()
    })
  })

  describe('license verification step', () => {
    it('replaces the entry choice instead of adding to it', async () => {
      renderApp()
      await goToLicenseVerification()

      expect(
        screen.getByText('Choose how to validate the license for this site.')
      ).toBeInTheDocument()
      expect(screen.getByText('Verify online')).toBeInTheDocument()
      expect(screen.getByText('Verify offline')).toBeInTheDocument()
      expect(screen.queryByText('Welcome to your new Checkmk site')).not.toBeInTheDocument()
      expect(screen.queryByText('Start a trial')).not.toBeInTheDocument()
    })

    it('does not persist the selection yet', async () => {
      renderApp()
      await goToLicenseVerification()

      expect(mockCmkAjax).not.toHaveBeenCalled()
      expect(mockLocationAssign).not.toHaveBeenCalled()
    })

    it('persists the selection and opens the online verification on "Verify online"', async () => {
      renderApp()
      await goToLicenseVerification()

      await user.click(screen.getByText('Verify online'))

      await waitFor(() => {
        expectCustomerSelectionSaved('online')
        expect(mockLocationAssign).toHaveBeenCalledWith(
          'wato.py?mode=edit_licensing_settings&online=1'
        )
      })
    })

    it('persists the selection and opens the offline verification on "Verify offline"', async () => {
      renderApp()
      await goToLicenseVerification()

      await user.click(screen.getByText('Verify offline'))

      await waitFor(() => {
        expectCustomerSelectionSaved('offline')
        expect(mockLocationAssign).toHaveBeenCalledWith(
          'wato.py?mode=licensing_offline_verification'
        )
      })
    })

    it('persists the selection and returns to the dashboard on "Verify later"', async () => {
      renderApp()
      await goToLicenseVerification()

      await user.click(screen.getByRole('button', { name: 'Verify later' }))

      await waitFor(() => {
        expectCustomerSelectionSaved()
        expect(mockLocationAssign).toHaveBeenCalledWith('index.py')
      })
    })

    it('returns to the undecided entry choice on "Back"', async () => {
      renderApp()
      await goToLicenseVerification()

      await user.click(screen.getByRole('button', { name: 'Back' }))

      expect(screen.getByText('Welcome to your new Checkmk site')).toBeInTheDocument()
      expect(screen.queryByText('Verify online')).not.toBeInTheDocument()
      expect(mockCmkAjax).not.toHaveBeenCalled()
    })

    it('blocks its buttons while a verification is still being saved', async () => {
      mockCmkAjax.mockReturnValue(new Promise(() => {}))
      renderApp()
      await goToLicenseVerification()

      await user.click(screen.getByText('Verify online'))
      await waitFor(() => {
        expect(mockCmkAjax).toHaveBeenCalledTimes(1)
      })

      expect(screen.getByRole('button', { name: 'Back' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'Verify later' })).toBeDisabled()
    })

    // The cards are not buttons: `disabled` only dims them, and keyboard activation
    // still reaches the callback. The guard on the save is what stops a second one.
    it('ignores a second verification while the first is still being saved', async () => {
      mockCmkAjax.mockReturnValue(new Promise(() => {}))
      renderApp()
      await goToLicenseVerification()

      await user.click(screen.getByText('Verify online'))
      await waitFor(() => {
        expect(mockCmkAjax).toHaveBeenCalledTimes(1)
      })

      await user.click(screen.getByText('Verify offline'))

      expect(mockCmkAjax).toHaveBeenCalledTimes(1)
      expectCustomerSelectionSaved('online')
    })

    it('keeps the user on the step and shows an error when saving fails', async () => {
      vi.spyOn(console, 'error').mockImplementation(() => {})
      renderApp()
      await goToLicenseVerification()
      mockCmkAjax.mockRejectedValue(new Error('nope'))

      await user.click(screen.getByText('Verify online'))

      await waitFor(() => {
        expect(
          screen.getByText('Saving your selection failed. Please try again.')
        ).toBeInTheDocument()
      })
      expect(screen.getByText('Verify offline')).toBeInTheDocument()
      expect(mockLocationAssign).not.toHaveBeenCalled()
    })
  })

  describe('email step', () => {
    it('returns to the entry choice on Back', async () => {
      renderApp()
      await startTrial()

      await user.click(screen.getByRole('button', { name: 'Back' }))

      expect(screen.getByText('Welcome to your new Checkmk site')).toBeInTheDocument()
      expect(mockCmkAjax).not.toHaveBeenCalled()
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

    it('accepts a well-formed address on Enter', async () => {
      renderApp()
      await startTrial()

      await user.type(screen.getByLabelText('Email address'), 'jane.doe@example.com{Enter}')

      expect(screen.getByText('Enter your verification code')).toBeInTheDocument()
      // Nothing leaves the site until CMK-37828 wires the send up.
      expect(mockCmkAjax).not.toHaveBeenCalled()
    })

    it('sends the code to the address without the whitespace around it', async () => {
      renderApp()
      await startTrial()

      await user.type(screen.getByLabelText('Email address'), '  jane.doe@example.com  ')
      await user.click(screen.getByRole('button', { name: 'Send code' }))

      expect(
        screen.getByText(
          'We sent a 6-digit code to jane.doe@example.com. It expires after 24 hours.'
        )
      ).toBeInTheDocument()
    })

    it('leaves the newsletter opt-in off, and does not toggle it from its own link', async () => {
      renderApp()
      await startTrial()

      const optIn = screen.getByRole('checkbox')
      expect(optIn).toHaveAttribute('aria-checked', 'false')

      // The legal notice below carries an unsubscribe link of its own; this is the one
      // inside the checkbox's label, where a plain click would activate the control as
      // its default action.
      const optInLink = screen.getByRole('link', {
        name: 'unsubscribe from the newsletter by email'
      })
      await user.click(optInLink)

      expect(optIn).toHaveAttribute('aria-checked', 'false')
    })
  })

  describe('code step', () => {
    it('names the address the code went to', async () => {
      renderApp()
      await reachCodeStep()

      expect(
        screen.getByText(
          'We sent a 6-digit code to jane.doe@example.com. It expires after 24 hours.'
        )
      ).toBeInTheDocument()
    })

    it('advances on the sixth digit without a click on Verify', async () => {
      renderApp()
      await reachCodeStep()

      await user.type(codeDigits()[0]!, '424242')

      expect(screen.queryByText('Enter your verification code')).not.toBeInTheDocument()
    })

    it('keeps Verify out of reach until the code is complete', async () => {
      renderApp()
      await reachCodeStep()

      expect(screen.getByRole('button', { name: 'Verify' })).toBeDisabled()

      await user.type(codeDigits()[0]!, '42424')

      expect(screen.getByRole('button', { name: 'Verify' })).toBeDisabled()
    })

    // The boxes submit themselves only when the last one is the box being filled, so a
    // code finished anywhere else is what Verify and Enter are there for.
    it('waits for Verify when the code is completed out of order', async () => {
      renderApp()
      await reachCodeStep()

      await typeCodeOutOfOrder()

      expect(screen.getByText('Enter your verification code')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Verify' })).toBeEnabled()
    })

    it('verifies on Enter when the code is completed out of order', async () => {
      renderApp()
      await reachCodeStep()
      await typeCodeOutOfOrder()

      await user.type(screen.getByRole('textbox', { name: 'Digit 6 of 6' }), '{Enter}')

      expect(screen.queryByText('Enter your verification code')).not.toBeInTheDocument()
    })

    it('puts the cursor in the first box, so the code can be typed straight away', async () => {
      renderApp()
      await reachCodeStep()

      await waitFor(() => {
        expect(screen.getByRole('textbox', { name: 'Digit 1 of 6' })).toHaveFocus()
      })
    })

    it('returns to the address on Back, with it still filled in', async () => {
      renderApp()
      await reachCodeStep()

      await user.click(screen.getByRole('button', { name: 'Back' }))

      expect(screen.getByLabelText('Email address')).toHaveValue('jane.doe@example.com')
    })
  })

  describe('resend cooldown', () => {
    beforeEach(() => {
      vi.useFakeTimers()
      // Handing user-event the fake clock rather than letting real elapsed time drive it:
      // the countdown then only moves where a test advances it, which is what makes the
      // exact seconds below exact rather than a race against how loaded the machine is.
      user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    function resendButton(): HTMLElement {
      return screen.getByRole('button', { name: /Resend code/ })
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
      expect(resendButton()).toHaveTextContent('Resend code (1:00)')
    })

    it('starts the cooldown over on a resend', async () => {
      renderApp()
      await reachCodeStep()

      await vi.advanceTimersByTimeAsync(60_000)
      await user.click(resendButton())

      expect(resendButton()).toHaveTextContent('Resend code (1:00)')
    })

    it('empties the boxes on a resend, the previous code being dead', async () => {
      renderApp()
      await reachCodeStep()

      const digits = () => codeDigits().map((input) => input.value)
      await user.type(codeDigits()[0]!, '42424')
      expect(digits()).toEqual(['4', '2', '4', '2', '4', ''])

      await vi.advanceTimersByTimeAsync(60_000)
      await user.click(resendButton())

      expect(digits()).toEqual(['', '', '', '', '', ''])
    })
  })
})
