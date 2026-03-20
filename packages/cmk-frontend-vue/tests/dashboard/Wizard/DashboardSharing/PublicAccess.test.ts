/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import PublicAccess from '@/dashboard/components/Wizard/wizards/dashboard-sharing/PublicAccess.vue'
import type { DashboardTokenModel } from '@/dashboard/components/Wizard/wizards/dashboard-sharing/api'
import * as api from '@/dashboard/components/Wizard/wizards/dashboard-sharing/api'
import { DashboardFeatures } from '@/dashboard/types/dashboard'

// PopupDialog uses Radix-Vue DialogPortal which does not work in jsdom.
// Replace it with a simple inline version that exposes buttons to the DOM.
vi.mock('@/dashboard/components/PopupDialog.vue', () => ({
  default: defineComponent({
    props: {
      open: { type: Boolean, default: false },
      title: String,
      message: [String, Array],
      buttons: Array,
      variant: String,
      dismissal_button: Object
    },
    emits: ['close'],
    setup(props, { emit }) {
      type Btn = { variant?: string; onclick?: () => void; title: string; testId?: string }
      type DismissalBtn = { title: string }
      return () => {
        if (!props.open) {
          return null
        }
        return h('div', { role: 'dialog', 'data-testid': 'popup-dialog' }, [
          props.title ? h('p', { 'data-testid': 'dialog-title' }, props.title as string) : null,
          ...((props.buttons as Btn[] | undefined) ?? []).map((btn: Btn) =>
            h(
              'button',
              {
                class: `cmk-button cmk-button--variant-${btn.variant ?? 'optional'}`,
                'data-testid': btn.testId,
                onClick: btn.onclick
              },
              btn.title
            )
          ),
          props.dismissal_button
            ? h(
                'button',
                { onClick: () => emit('close') },
                (props.dismissal_button as DismissalBtn).title
              )
            : null
        ])
      }
    }
  })
}))

// Stub sub-components that are not under test here.
vi.mock('@/dashboard/components/Wizard/wizards/dashboard-sharing/PublicAccessSettings.vue', () => ({
  default: defineComponent({
    name: 'PublicAccessSettings',
    template: '<div data-testid="public-access-settings" />'
  })
}))

vi.mock(
  '@/dashboard/components/Wizard/wizards/dashboard-sharing/RuntimeFiltersWarning.vue',
  () => ({
    default: defineComponent({
      name: 'RuntimeFiltersWarning',
      emits: ['reviewFilters'],
      template:
        '<div data-testid="runtime-filters-warning"><button @click="$emit(\'reviewFilters\')">Review filters</button></div>'
    })
  })
)

// Mock API so no real HTTP calls are made.
vi.mock('@/dashboard/components/Wizard/wizards/dashboard-sharing/api', () => ({
  createToken: vi.fn().mockResolvedValue({ token_id: 'new-tok', is_disabled: false }),
  deleteToken: vi.fn().mockResolvedValue(undefined),
  updateToken: vi.fn().mockResolvedValue({ token_id: 'upd-tok', is_disabled: false })
}))

// Also mock urlHandler.getSharedDashboardLink to return a predictable URL.
vi.mock('@/dashboard/utils', () => ({
  urlHandler: {
    getSharedDashboardLink: (tokenId: string) => `https://example.com/shared?token=${tokenId}`
  }
}))

const makeToken = (overrides: Partial<DashboardTokenModel> = {}): DashboardTokenModel => ({
  token_id: 'tok-abc',
  is_disabled: false,
  expires_at: null,
  issued_at: '',
  comment: '',
  ...overrides
})

const defaultKey = { name: 'my-dash', owner: 'admin' }

const renderPublicAccess = (
  props: {
    publicToken?: DashboardTokenModel | null
    dashboardFeatures?: DashboardFeatures
    hasRuntimeFilters?: boolean
  } = {}
) =>
  render(PublicAccess, {
    props: {
      dashboardKey: defaultKey,
      publicToken: null,
      dashboardFeatures: DashboardFeatures.UNRESTRICTED,
      hasRuntimeFilters: false,
      ...props
    }
  })

describe('PublicAccess', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Without a public token', () => {
    it('shows the "Generate public link" button', () => {
      renderPublicAccess()
      expect(screen.getByRole('button', { name: 'Generate public link' })).toBeInTheDocument()
    })

    it('does not show the public URL area', () => {
      renderPublicAccess()
      expect(screen.queryByText('Public dashboard URL')).not.toBeInTheDocument()
    })

    it('does not show PublicAccessSettings', () => {
      renderPublicAccess()
      expect(screen.queryByTestId('public-access-settings')).not.toBeInTheDocument()
    })
  })

  describe('With an active public token (is_disabled=false)', () => {
    const token = makeToken({ token_id: 'tok-abc', is_disabled: false })

    it('shows the public dashboard URL label', () => {
      renderPublicAccess({ publicToken: token })
      expect(screen.getByText('Public dashboard URL')).toBeInTheDocument()
    })

    it('shows the shared link in the code block', () => {
      renderPublicAccess({ publicToken: token })
      expect(screen.getByText('https://example.com/shared?token=tok-abc')).toBeInTheDocument()
    })

    it('shows "Disable access" button when token is active', () => {
      renderPublicAccess({ publicToken: token })
      expect(screen.getByRole('button', { name: 'Disable access' })).toBeInTheDocument()
    })

    it('does not show "Enable access" button when token is active', () => {
      renderPublicAccess({ publicToken: token })
      expect(screen.queryByRole('button', { name: 'Enable access' })).not.toBeInTheDocument()
    })

    it('shows a "Delete" link', () => {
      renderPublicAccess({ publicToken: token })
      expect(screen.getByRole('link', { name: 'Delete' })).toBeInTheDocument()
    })

    it('shows PublicAccessSettings', () => {
      renderPublicAccess({ publicToken: token })
      expect(screen.getByTestId('public-access-settings')).toBeInTheDocument()
    })
  })

  describe('With a disabled public token (is_disabled=true)', () => {
    const token = makeToken({ is_disabled: true })

    it('shows "Enable access" button', () => {
      renderPublicAccess({ publicToken: token })
      expect(screen.getByRole('button', { name: 'Enable access' })).toBeInTheDocument()
    })

    it('does not show "Disable access" button', () => {
      renderPublicAccess({ publicToken: token })
      expect(screen.queryByRole('button', { name: 'Disable access' })).not.toBeInTheDocument()
    })
  })

  describe('Runtime filters warning', () => {
    it('shows RuntimeFiltersWarning instead of creating a token when hasRuntimeFilters=true', async () => {
      renderPublicAccess({ hasRuntimeFilters: true })

      await fireEvent.click(screen.getByRole('button', { name: 'Generate public link' }))

      expect(screen.getByTestId('runtime-filters-warning')).toBeInTheDocument()
      expect(api.createToken).not.toHaveBeenCalled()
    })

    it('emits reviewFilters when the warning button is clicked', async () => {
      const { emitted } = renderPublicAccess({ hasRuntimeFilters: true })

      await fireEvent.click(screen.getByRole('button', { name: 'Generate public link' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Review filters' }))

      expect(emitted()['reviewFilters']).toHaveLength(1)
    })

    it('shows RuntimeFiltersWarning when enabling an active token with runtime filters', async () => {
      const token = makeToken({ is_disabled: true })
      renderPublicAccess({ publicToken: token, hasRuntimeFilters: true })

      await fireEvent.click(screen.getByRole('button', { name: 'Enable access' }))

      expect(screen.getByTestId('runtime-filters-warning')).toBeInTheDocument()
    })
  })

  describe('Create token flow', () => {
    it('calls createToken API and emits refreshDashboardSettings on success', async () => {
      const { emitted } = renderPublicAccess()

      await fireEvent.click(screen.getByRole('button', { name: 'Generate public link' }))
      await flushPromises()

      expect(api.createToken).toHaveBeenCalledOnce()
      expect(emitted()['refreshDashboardSettings']).toHaveLength(1)
    })
  })

  describe('Delete token flow', () => {
    it('opens a confirmation dialog when "Delete" is clicked', async () => {
      renderPublicAccess({ publicToken: makeToken() })

      await fireEvent.click(screen.getByRole('link', { name: 'Delete' }))

      expect(screen.getByTestId('popup-dialog')).toBeInTheDocument()
    })

    it('calls deleteToken API and emits refreshDashboardSettings after dialog confirmation', async () => {
      const { emitted } = renderPublicAccess({ publicToken: makeToken() })

      await fireEvent.click(screen.getByRole('link', { name: 'Delete' }))
      // Click the confirm button inside the mocked dialog
      await fireEvent.click(screen.getByRole('button', { name: 'Delete public link?' }))
      await flushPromises()

      expect(api.deleteToken).toHaveBeenCalledOnce()
      expect(emitted()['refreshDashboardSettings']).toHaveLength(1)
    })

    it('does not call deleteToken if dialog Cancel is clicked', async () => {
      renderPublicAccess({ publicToken: makeToken() })

      await fireEvent.click(screen.getByRole('link', { name: 'Delete' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
      await flushPromises()

      expect(api.deleteToken).not.toHaveBeenCalled()
    })
  })

  describe('Disable access flow', () => {
    it('opens a confirmation dialog when "Disable access" is clicked', async () => {
      renderPublicAccess({ publicToken: makeToken({ is_disabled: false }) })

      await fireEvent.click(screen.getByRole('button', { name: 'Disable access' }))

      expect(screen.getByTestId('popup-dialog')).toBeInTheDocument()
    })

    it('calls updateToken API and emits refreshDashboardSettings after confirming disable', async () => {
      const { emitted } = renderPublicAccess({ publicToken: makeToken({ is_disabled: false }) })
      await fireEvent.click(screen.getByRole('button', { name: 'Disable access' }))
      await fireEvent.click(screen.getByTestId('disable-access-popup-action'))
      await flushPromises()

      expect(api.updateToken).toHaveBeenCalledOnce()
      expect(emitted()['refreshDashboardSettings']).toHaveLength(1)
    })
  })

  describe('Enable access flow', () => {
    it('opens a confirmation dialog when "Enable access" is clicked', async () => {
      renderPublicAccess({ publicToken: makeToken({ is_disabled: true }) })

      await fireEvent.click(screen.getByRole('button', { name: 'Enable access' }))

      expect(screen.getByTestId('popup-dialog')).toBeInTheDocument()
    })

    it('calls updateToken API and emits refreshDashboardSettings after confirming enable', async () => {
      const { emitted } = renderPublicAccess({ publicToken: makeToken({ is_disabled: true }) })

      await fireEvent.click(screen.getByRole('button', { name: 'Enable access' }))
      await fireEvent.click(screen.getByTestId('enable-access-popup-action'))
      await flushPromises()

      expect(api.updateToken).toHaveBeenCalledOnce()
      expect(emitted()['refreshDashboardSettings']).toHaveLength(1)
    })
  })

  describe('Action in progress', () => {
    it('disables the "Generate public link" button while a create action is in progress', async () => {
      // Make createToken hang so we can inspect the in-progress state
      vi.mocked(api.createToken).mockReturnValueOnce(new Promise(() => {}))

      renderPublicAccess()

      const button = screen.getByRole('button', { name: 'Generate public link' })
      await fireEvent.click(button)

      expect(button).toBeDisabled()
    })
  })
})
