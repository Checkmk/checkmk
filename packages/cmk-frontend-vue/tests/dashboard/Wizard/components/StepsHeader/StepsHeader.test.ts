/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import StepsHeader from '@/dashboard/components/Wizard/components/StepsHeader.vue'

describe('StepsHeader', () => {
  describe('Rendering', () => {
    it('renders the title', () => {
      render(StepsHeader, { props: { title: 'My Wizard' } })
      expect(screen.getByText('My Wizard')).toBeInTheDocument()
    })

    it('renders the subtitle when provided', () => {
      render(StepsHeader, { props: { title: 'My Wizard', subtitle: 'Step 1 of 3' } })
      expect(screen.getByText('Step 1 of 3')).toBeInTheDocument()
    })

    it('does not render the subtitle when not provided', () => {
      render(StepsHeader, { props: { title: 'My Wizard' } })
      expect(screen.queryByText('Step 1 of 3')).not.toBeInTheDocument()
    })

    it('renders the back icon when hideBackButton is false', () => {
      render(StepsHeader, { props: { title: 'My Wizard', hideBackButton: false } })
      expect(screen.getByRole('button', { name: 'Back' })).toBeInTheDocument()
    })

    it('hides the back icon when hideBackButton is true', () => {
      render(StepsHeader, { props: { title: 'My Wizard', hideBackButton: true } })
      expect(screen.queryByRole('button', { name: 'Back' })).not.toBeInTheDocument()
    })

    it('shows the back icon by default', () => {
      render(StepsHeader, { props: { title: 'My Wizard' } })
      expect(screen.getByRole('button', { name: 'Back' })).toBeInTheDocument()
    })

    it('renders the close button when closeButton is true', () => {
      render(StepsHeader, {
        props: { title: 'My Wizard', hideBackButton: true, closeButton: true }
      })
      expect(screen.getByRole('button', { name: 'Close' })).toBeInTheDocument()
    })

    it('does not render the close button when closeButton is false', () => {
      render(StepsHeader, { props: { title: 'My Wizard', closeButton: false } })
      expect(screen.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument()
    })
  })

  describe('Events', () => {
    it('emits "back" when the back icon is clicked', async () => {
      const { emitted } = render(StepsHeader, {
        props: { title: 'My Wizard', hideBackButton: false }
      })
      await fireEvent.click(screen.getByRole('button', { name: 'Back' }))
      expect(emitted()['back']).toHaveLength(1)
    })

    it('emits "back" when the close button is clicked', async () => {
      const { emitted } = render(StepsHeader, {
        props: { title: 'My Wizard', hideBackButton: true, closeButton: true }
      })
      await fireEvent.click(screen.getByRole('button', { name: 'Close' }))
      expect(emitted()['back']).toHaveLength(1)
    })

    it('does not emit "back" before any interaction', () => {
      const { emitted } = render(StepsHeader, { props: { title: 'My Wizard' } })
      expect(emitted()['back']).toBeUndefined()
    })
  })
})
