/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'

import ActionButton from '@/dashboard/components/Wizard/components/ActionButton.vue'

describe('ActionButton', () => {
  describe('Rendering', () => {
    it('renders the label text', () => {
      render(ActionButton, { props: { label: 'Create', action: vi.fn() } })
      expect(screen.getByRole('button')).toHaveTextContent('Create')
    })

    it('renders a button element', () => {
      render(ActionButton, { props: { label: 'Create', action: vi.fn() } })
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('renders the icon before the label when icon.side is "left"', () => {
      render(ActionButton, {
        props: {
          label: 'Cancel',
          icon: { name: 'cancel', side: 'left' },
          action: vi.fn()
        }
      })
      const button = screen.getByRole('button')
      expect(button.firstElementChild).toBe(screen.getByRole('img'))
    })

    it('renders the icon after the label when icon.side is "right"', () => {
      render(ActionButton, {
        props: {
          label: 'Next',
          icon: { name: 'checkmk-logo', side: 'right' },
          action: vi.fn()
        }
      })
      const button = screen.getByRole('button')
      expect(button).toHaveTextContent('Next')
      expect(button.lastElementChild).toBe(screen.getByRole('img'))
    })

    it('renders no icon when none is provided', () => {
      render(ActionButton, { props: { label: 'Create', action: vi.fn() } })
      expect(screen.queryByRole('img')).not.toBeInTheDocument()
    })

    it('renders the icon before the label when icon.side is omitted', () => {
      render(ActionButton, {
        props: { label: 'Save', icon: { name: 'save' }, action: vi.fn() }
      })
      const button = screen.getByRole('button')
      expect(button.firstElementChild).toBe(screen.getByRole('img'))
    })
  })

  describe('Actions', () => {
    it('calls the action function when clicked', async () => {
      const action = vi.fn()
      render(ActionButton, { props: { label: 'Create', action } })
      await fireEvent.click(screen.getByRole('button'))
      expect(action).toHaveBeenCalledOnce()
    })

    it('calls the action on every click', async () => {
      const action = vi.fn()
      render(ActionButton, { props: { label: 'Create', action } })
      const button = screen.getByRole('button')
      await fireEvent.click(button)
      await fireEvent.click(button)
      expect(action).toHaveBeenCalledTimes(2)
    })
  })
})
