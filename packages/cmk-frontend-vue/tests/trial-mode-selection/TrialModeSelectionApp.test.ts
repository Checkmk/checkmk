/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import TrialModeSelectionApp from '@/trial-mode-selection/TrialModeSelectionApp.vue'

const mockCmkAjax = vi.hoisted(() => vi.fn().mockResolvedValue({}))

vi.mock('cmk-ui-library/lib/ajax', () => ({
  cmkAjax: mockCmkAjax
}))

const mockLocationAssign = vi.fn()

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
  await userEvent.click(screen.getByText('Start a trial'))
}

async function goToLicenseVerification() {
  await userEvent.click(screen.getByText("I'm an existing customer"))
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

    await userEvent.click(screen.getByRole('button', { name: 'Back' }))
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

      await userEvent.click(screen.getByText('Verify online'))

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

      await userEvent.click(screen.getByText('Verify offline'))

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

      await userEvent.click(screen.getByRole('button', { name: 'Verify later' }))

      await waitFor(() => {
        expectCustomerSelectionSaved()
        expect(mockLocationAssign).toHaveBeenCalledWith('index.py')
      })
    })

    it('returns to the undecided entry choice on "Back"', async () => {
      renderApp()
      await goToLicenseVerification()

      await userEvent.click(screen.getByRole('button', { name: 'Back' }))

      expect(screen.getByText('Welcome to your new Checkmk site')).toBeInTheDocument()
      expect(screen.queryByText('Verify online')).not.toBeInTheDocument()
      expect(mockCmkAjax).not.toHaveBeenCalled()
    })

    it('blocks its buttons while a verification is still being saved', async () => {
      mockCmkAjax.mockReturnValue(new Promise(() => {}))
      renderApp()
      await goToLicenseVerification()

      await userEvent.click(screen.getByText('Verify online'))
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

      await userEvent.click(screen.getByText('Verify online'))
      await waitFor(() => {
        expect(mockCmkAjax).toHaveBeenCalledTimes(1)
      })

      await userEvent.click(screen.getByText('Verify offline'))

      expect(mockCmkAjax).toHaveBeenCalledTimes(1)
      expectCustomerSelectionSaved('online')
    })

    it('keeps the user on the step and shows an error when saving fails', async () => {
      vi.spyOn(console, 'error').mockImplementation(() => {})
      renderApp()
      await goToLicenseVerification()
      mockCmkAjax.mockRejectedValue(new Error('nope'))

      await userEvent.click(screen.getByText('Verify online'))

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

      await userEvent.click(screen.getByRole('button', { name: 'Back' }))

      expect(screen.getByText('Welcome to your new Checkmk site')).toBeInTheDocument()
      expect(mockCmkAjax).not.toHaveBeenCalled()
    })

    it('rejects a malformed address instead of advancing', async () => {
      renderApp()
      await startTrial()

      await userEvent.type(screen.getByLabelText('Email address'), 'jane.doe@example')
      await userEvent.click(screen.getByRole('button', { name: 'Send code' }))

      expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument()
      expect(screen.getByText('Verify your email address')).toBeInTheDocument()
    })

    it('clears the complaint as soon as the address is edited again', async () => {
      renderApp()
      await startTrial()

      await userEvent.click(screen.getByRole('button', { name: 'Send code' }))
      expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument()

      await userEvent.type(screen.getByLabelText('Email address'), 'j')

      expect(screen.queryByText('Enter a valid email address.')).not.toBeInTheDocument()
    })

    it('accepts a well-formed address on Enter', async () => {
      renderApp()
      await startTrial()

      await userEvent.type(screen.getByLabelText('Email address'), 'jane.doe@example.com{Enter}')

      expect(screen.queryByText('Enter a valid email address.')).not.toBeInTheDocument()
      // The code step arrives with CMK-37568's next change, so a valid address stays put
      // here rather than navigating to a screen that has nothing to render.
      expect(screen.getByText('Verify your email address')).toBeInTheDocument()
      expect(mockCmkAjax).not.toHaveBeenCalled()
    })

    it('trims the whitespace around the address', async () => {
      renderApp()
      await startTrial()

      await userEvent.type(screen.getByLabelText('Email address'), '  jane.doe@example.com  ')
      await userEvent.click(screen.getByRole('button', { name: 'Send code' }))

      expect(screen.getByLabelText('Email address')).toHaveValue('jane.doe@example.com')
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
      await userEvent.click(optInLink)

      expect(optIn).toHaveAttribute('aria-checked', 'false')
    })
  })
})
