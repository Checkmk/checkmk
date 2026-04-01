/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import ActionBar from '@/dashboard/components/Wizard/components/ActionBar.vue'

describe('ActionBar', () => {
  describe('Rendering', () => {
    it('renders slotted content', () => {
      render(ActionBar, {
        slots: { default: '<button>Primary</button><button>Secondary</button>' }
      })
      expect(screen.getByText('Primary')).toBeInTheDocument()
      expect(screen.getByText('Secondary')).toBeInTheDocument()
    })

    it('renders the db-action-bar container', () => {
      const { container } = render(ActionBar)
      expect(container.querySelector('.db-action-bar')).toBeInTheDocument()
    })

    it('renders empty content when no slot is provided', () => {
      const { container } = render(ActionBar)
      const bar = container.querySelector('.db-action-bar')!
      expect(bar.children).toHaveLength(0)
    })
  })
})
