/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

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
      verify_online_url: 'wato.py?mode=licensing',
      verify_offline_url: 'wato.py?mode=licensing',
      user_name: 'cmkadmin'
    }
  })
}

function goToVerificationStep() {
  renderApp()
  screen.getByText("I'm an existing customer").click()
  return screen.findByText('Verify your license')
}

function expectCustomerSelectionSaved() {
  expect(mockCmkAjax).toHaveBeenCalledWith('ajax_save_trial_mode_selection.py', {
    selection: 'customer',
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

  it('persists the trial selection and redirects to the dashboard', async () => {
    renderApp()
    screen.getByText('Start a trial').click()
    await waitFor(() => {
      expect(mockCmkAjax).toHaveBeenCalledWith('ajax_save_trial_mode_selection.py', {
        selection: 'trial',
        _csrf_token: 'the-csrf-token'
      })
      expect(mockLocationAssign).toHaveBeenCalledWith('index.py')
    })
  })

  it('shows an error and does not redirect when saving fails', async () => {
    mockCmkAjax.mockRejectedValue(new Error('nope'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    renderApp()
    screen.getByText('Start a trial').click()
    await waitFor(() => {
      expect(
        screen.getByText('Saving your selection failed. Please try again.')
      ).toBeInTheDocument()
    })
    expect(mockLocationAssign).not.toHaveBeenCalled()
  })

  describe('verification step', () => {
    it('is shown when the existing customer option is picked', async () => {
      renderApp()
      expect(screen.queryByText('Verify your license')).not.toBeInTheDocument()

      screen.getByText("I'm an existing customer").click()

      expect(await screen.findByText('Verify your license')).toBeInTheDocument()
    })

    it('offers both verification options once the customer step is entered', async () => {
      await goToVerificationStep()
      expect(
        screen.getByText('Choose how to validate the license for this site.')
      ).toBeInTheDocument()
      expect(screen.getByText('Verify online')).toBeInTheDocument()
      expect(screen.getByText('Verify offline')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Back' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Verify later' })).toBeInTheDocument()
    })

    it('replaces the mode selection instead of adding to it', async () => {
      await goToVerificationStep()
      expect(screen.queryByText('Welcome to your new Checkmk site')).not.toBeInTheDocument()
      expect(screen.queryByText('Start a trial')).not.toBeInTheDocument()
      expect(screen.queryByText("I'm an existing customer")).not.toBeInTheDocument()
    })

    it('moves the focus to the heading of the new step', async () => {
      await goToVerificationStep()
      await waitFor(() => {
        expect(screen.getByText('Verify your license')).toHaveFocus()
      })

      screen.getByRole('button', { name: 'Back' }).click()
      await waitFor(() => {
        expect(screen.getByText('Welcome to your new Checkmk site')).toHaveFocus()
      })
    })

    it('still offers logging out', async () => {
      await goToVerificationStep()
      expect(screen.getByRole('link', { name: 'Log out' })).toHaveAttribute('href', 'logout.py')
    })

    it('does not persist the selection yet', async () => {
      await goToVerificationStep()
      expect(mockCmkAjax).not.toHaveBeenCalled()
      expect(mockLocationAssign).not.toHaveBeenCalled()
    })

    it('persists the selection and opens the online verification on "Verify online"', async () => {
      await goToVerificationStep()
      screen.getByText('Verify online').click()
      await waitFor(() => {
        expectCustomerSelectionSaved()
        expect(mockLocationAssign).toHaveBeenCalledWith('wato.py?mode=licensing')
      })
    })

    it('persists the selection and opens the offline verification on "Verify offline"', async () => {
      await goToVerificationStep()
      screen.getByText('Verify offline').click()
      await waitFor(() => {
        expectCustomerSelectionSaved()
        expect(mockLocationAssign).toHaveBeenCalledWith('wato.py?mode=licensing')
      })
    })

    it('persists the selection and returns to the dashboard on "Verify later"', async () => {
      await goToVerificationStep()
      screen.getByRole('button', { name: 'Verify later' }).click()
      await waitFor(() => {
        expectCustomerSelectionSaved()
        expect(mockLocationAssign).toHaveBeenCalledWith('index.py')
      })
    })

    it('returns to the undecided mode selection on "Back"', async () => {
      await goToVerificationStep()
      screen.getByRole('button', { name: 'Back' }).click()
      expect(await screen.findByText('Welcome to your new Checkmk site')).toBeInTheDocument()
      expect(screen.queryByText('Verify online')).not.toBeInTheDocument()
      expect(mockCmkAjax).not.toHaveBeenCalled()
    })

    it('is not entered while another selection is still being saved', async () => {
      let finishSaving: () => void = () => {}
      mockCmkAjax.mockReturnValue(
        new Promise<void>((resolve) => {
          finishSaving = () => {
            resolve()
          }
        })
      )
      renderApp()
      screen.getByText('Start a trial').click()
      await waitFor(() => {
        expect(mockCmkAjax).toHaveBeenCalledTimes(1)
      })

      screen.getByText("I'm an existing customer").click()
      await nextTick()
      expect(screen.queryByText('Verify your license')).not.toBeInTheDocument()

      finishSaving()
      await waitFor(() => {
        expect(mockLocationAssign).toHaveBeenCalledWith('index.py')
      })
    })

    it('blocks its buttons while a verification is still being saved', async () => {
      mockCmkAjax.mockReturnValue(new Promise(() => {}))
      await goToVerificationStep()

      screen.getByText('Verify online').click()
      await waitFor(() => {
        expect(mockCmkAjax).toHaveBeenCalledTimes(1)
      })

      expect(screen.getByRole('button', { name: 'Back' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'Verify later' })).toBeDisabled()
    })

    it('keeps the user on the step and shows an error when saving fails', async () => {
      vi.spyOn(console, 'error').mockImplementation(() => {})
      await goToVerificationStep()
      mockCmkAjax.mockRejectedValue(new Error('nope'))
      screen.getByText('Verify online').click()
      await waitFor(() => {
        expect(
          screen.getByText('Saving your selection failed. Please try again.')
        ).toBeInTheDocument()
      })
      expect(screen.getByText('Verify offline')).toBeInTheDocument()
      expect(mockLocationAssign).not.toHaveBeenCalled()
    })
  })
})
