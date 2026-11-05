/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import TrialModeSelectionEmailEntry from '@/trial-mode-selection/screens/TrialModeSelectionEmailEntry.vue'

function renderEmailEntry(): void {
  render(TrialModeSelectionEmailEntry, { props: { email: '', trialLengthDays: 30 } })
}

describe('TrialModeSelectionEmailEntry', () => {
  it('opens every legal link in a new tab so the dialog stays open', () => {
    renderEmailEntry()

    const links = screen.getAllByRole('link')

    expect(links.length).toBeGreaterThan(0)
    for (const link of links) {
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener')
    }
  })
})
