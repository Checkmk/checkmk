/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, markRaw } from 'vue'

import DashboardSharingWizard from '@/dashboard/components/Wizard/wizards/dashboard-sharing/DashboardSharingWizard.vue'
import type { DashboardTokenModel } from '@/dashboard/components/Wizard/wizards/dashboard-sharing/api'
import { DashboardFeatures } from '@/dashboard/types/dashboard'

// markRaw: a reactive proxy can't be structuredClone'd under vitest.
const exampleToken: DashboardTokenModel = markRaw({
  token_id: 'tok-abc',
  is_disabled: false,
  expires_at: null,
  issued_at: '',
  comment: ''
})

// CmkSlideIn uses Radix-Vue DialogPortal which doesn't work in jsdom.
vi.mock('@/components/CmkSlideIn', () => ({
  default: defineComponent({
    name: 'CmkSlideIn',
    setup(_, { slots }) {
      return () => h('div', { 'data-testid': 'slide-in' }, slots.default?.())
    }
  })
}))

// Stub child wizards so this test focuses on the wrapper behaviour only.
vi.mock('@/dashboard/components/Wizard/wizards/dashboard-sharing/InternalAccess.vue', () => ({
  default: defineComponent({
    name: 'InternalAccess',
    props: { dashboardUrl: { type: String, required: true } },
    template: '<div data-testid="internal-access" :data-url="dashboardUrl" />'
  })
}))

vi.mock('@/dashboard/components/Wizard/wizards/dashboard-sharing/PublicAccess.vue', () => ({
  default: defineComponent({
    name: 'PublicAccess',
    props: {
      dashboardKey: { type: Object, required: true },
      publicToken: { type: Object, default: null },
      dashboardFeatures: { type: String, required: true },
      hasRuntimeFilters: { type: Boolean, required: true }
    },
    emits: ['reviewFilters', 'refreshDashboardSettings'],
    template: '<div data-testid="public-access" />'
  })
}))

const defaultProps = {
  dashboardKey: { name: 'my-dash', owner: 'admin' },
  publicToken: null,
  dashboardFeatures: DashboardFeatures.UNRESTRICTED,
  hasRuntimeFilters: false,
  mayLinkShare: true
}

describe('DashboardSharingWizard', () => {
  describe('Rendering', () => {
    it('renders the "Configure sharing" heading', () => {
      render(DashboardSharingWizard, { props: defaultProps })
      expect(screen.getByText('Configure sharing')).toBeInTheDocument()
    })

    it('renders a "Close" button', () => {
      render(DashboardSharingWizard, { props: defaultProps })
      expect(screen.getByRole('button', { name: 'Close' })).toBeInTheDocument()
    })

    it('renders the InternalAccess section', () => {
      render(DashboardSharingWizard, { props: defaultProps })
      expect(screen.getByTestId('internal-access')).toBeInTheDocument()
    })

    it('renders the PublicAccess section when the user may link-share', () => {
      render(DashboardSharingWizard, { props: defaultProps })
      expect(screen.getByTestId('public-access')).toBeInTheDocument()
    })

    it('hides the PublicAccess section without permission and without a link', () => {
      render(DashboardSharingWizard, { props: { ...defaultProps, mayLinkShare: false } })
      expect(screen.queryByTestId('public-access')).not.toBeInTheDocument()
    })

    it('still shows the PublicAccess section without permission if a link exists', () => {
      render(DashboardSharingWizard, {
        props: { ...defaultProps, mayLinkShare: false, publicToken: exampleToken }
      })
      expect(screen.getByTestId('public-access')).toBeInTheDocument()
    })
  })

  describe('dashboardUrl prop', () => {
    it('passes a non-empty URL string to InternalAccess', () => {
      render(DashboardSharingWizard, { props: defaultProps })
      const el = screen.getByTestId('internal-access')
      expect(el.dataset['url']).toBeTruthy()
    })

    it('uses window.location.href as the URL', () => {
      render(DashboardSharingWizard, { props: defaultProps })
      const el = screen.getByTestId('internal-access')
      // jsdom sets window.location.href; window.parent.location.href falls back to it.
      expect(el.dataset['url']).toContain('localhost')
    })
  })

  describe('Emits', () => {
    it('emits "close" when the Close button is clicked', async () => {
      const { emitted } = render(DashboardSharingWizard, { props: defaultProps })
      await fireEvent.click(screen.getByRole('button', { name: 'Close' }))
      expect(emitted()['close']).toHaveLength(1)
    })

    it('emits "close" when the X CloseButton icon is clicked', async () => {
      const { emitted } = render(DashboardSharingWizard, { props: defaultProps })
      const closeIconButton = screen.getByTestId('icon-x-close-button')
      await fireEvent.click(closeIconButton)
      expect(emitted()['close']).toHaveLength(1)
    })
  })
})
