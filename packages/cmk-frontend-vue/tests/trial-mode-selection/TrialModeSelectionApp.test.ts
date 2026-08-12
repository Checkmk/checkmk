/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
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
      user_name: 'cmkadmin'
    }
  })
}

describe('TrialModeSelectionApp', () => {
  beforeEach(() => {
    mockCmkAjax.mockClear()
    mockCmkAjax.mockResolvedValue({})
    mockLocationAssign.mockClear()
    vi.stubGlobal('global_csrf_token', 'the-csrf-token')
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

  it('persists the customer selection and redirects to the dashboard', async () => {
    renderApp()
    screen.getByText("I'm an existing customer").click()
    await waitFor(() => {
      expect(mockCmkAjax).toHaveBeenCalledWith('ajax_save_trial_mode_selection.py', {
        selection: 'customer',
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
})
