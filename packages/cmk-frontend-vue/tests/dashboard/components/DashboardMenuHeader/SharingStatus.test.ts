/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import SharingStatus from '@/dashboard/components/DashboardMenuHeader/SharingStatus.vue'

function renderSharingStatus(props: {
  sharingState: 'disabled' | 'paused' | 'active'
  sharedUntil?: Date | null
}) {
  return render(SharingStatus, { props })
}

function daysFromNow(days: number): Date {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d
}

describe('SharingStatus', () => {
  describe('sharing state without expiry', () => {
    it('shows disabled state', () => {
      renderSharingStatus({ sharingState: 'disabled' })
      expect(screen.getByText('Sharing')).toBeInTheDocument()
      expect(screen.getByText('disabled')).toBeInTheDocument()
    })

    it('shows paused state', () => {
      renderSharingStatus({ sharingState: 'paused' })
      expect(screen.getByText('Sharing')).toBeInTheDocument()
      expect(screen.getByText('paused')).toBeInTheDocument()
    })

    it('shows active state without expiry date', () => {
      renderSharingStatus({ sharingState: 'active' })
      expect(screen.getByText('Sharing')).toBeInTheDocument()
      expect(screen.getByText('active')).toBeInTheDocument()
    })
  })

  describe('active state with expiry dates', () => {
    it('shows date when expiry is more than 7 days away', () => {
      const futureDate = daysFromNow(30)
      renderSharingStatus({ sharingState: 'active', sharedUntil: futureDate })
      expect(screen.getByText('Sharing until')).toBeInTheDocument()
    })

    it('shows "expires in N days" when expiry is 2-7 days away', () => {
      renderSharingStatus({ sharingState: 'active', sharedUntil: daysFromNow(5) })
      expect(screen.getByText('Sharing')).toBeInTheDocument()
      expect(screen.getByText('expires in 5 days')).toBeInTheDocument()
    })

    it('shows "expires in 1 day" when expiry is 1 day away', () => {
      renderSharingStatus({ sharingState: 'active', sharedUntil: daysFromNow(1) })
      expect(screen.getByText('Sharing')).toBeInTheDocument()
      expect(screen.getByText('expires in 1 day')).toBeInTheDocument()
    })

    it('shows "expires today" when expiry is today', () => {
      const today = new Date()
      today.setHours(today.getHours() - 1)
      renderSharingStatus({ sharingState: 'active', sharedUntil: today })
      expect(screen.getByText('Sharing')).toBeInTheDocument()
      expect(screen.getByText('expires today')).toBeInTheDocument()
    })

    it('shows expired state when date is in the past', () => {
      const pastDate = daysFromNow(-5)
      renderSharingStatus({ sharingState: 'active', sharedUntil: pastDate })
      expect(screen.getByText('Sharing expired on')).toBeInTheDocument()
      expect(screen.getByText(pastDate.toISOString().split('T')[0]!)).toBeInTheDocument()
    })
  })

  describe('emits', () => {
    it('emits openSharingSettings when linked text is clicked', async () => {
      const { emitted } = renderSharingStatus({ sharingState: 'active' })
      const link = screen.getByText('active')
      await link.click()
      expect(emitted()['openSharingSettings']).toHaveLength(1)
    })
  })
})
