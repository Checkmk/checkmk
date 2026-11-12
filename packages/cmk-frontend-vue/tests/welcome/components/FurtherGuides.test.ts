/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import FurtherGuides from '@/welcome/components/FurtherGuides.vue'

import { createMockCards } from '../mockCards'

const ASSIGN = 'Assign responsibilities with contact groups'
const ADJUST = 'Adjust service thresholds'

test('open guides list the guides not finished yet', () => {
  render(FurtherGuides, {
    props: { cards: createMockCards(), finishedSteps: ['assign_responsibilities'], show: 'open' }
  })

  expect(screen.getByText(ADJUST)).toBeInTheDocument()
  expect(screen.queryByText(ASSIGN)).not.toBeInTheDocument()
})

test('done guides list only the finished guides', () => {
  render(FurtherGuides, {
    props: { cards: createMockCards(), finishedSteps: ['assign_responsibilities'], show: 'done' }
  })

  expect(screen.getByText(ASSIGN)).toBeInTheDocument()
  expect(screen.queryByText(ADJUST)).not.toBeInTheDocument()
})
