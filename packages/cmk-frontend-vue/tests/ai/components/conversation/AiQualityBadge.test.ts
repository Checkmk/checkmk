/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import AiQualityBadge from '@/ai/components/conversation/AiQualityBadge.vue'
import type { QualityLevel } from '@/ai/lib/markdown'

function renderAiQualityBadge(level: QualityLevel | null): ReturnType<typeof render> {
  return render(AiQualityBadge, {
    props: { level },
    global: {
      stubs: {
        CmkIcon: true,
        CmkProgressCircle: true,
        CmkTooltipProvider: { template: '<div><slot /></div>' },
        CmkTooltip: { template: '<div><slot /></div>' },
        CmkTooltipTrigger: { template: '<div><slot /></div>' },
        CmkTooltipContent: { template: '<div><slot /></div>' }
      }
    }
  })
}

test.each([
  ['high', 'Data quality: High'],
  ['medium', 'Data quality: Medium'],
  ['low', 'Data quality: Low']
] as const)('exposes the %s badge as role=img with its accessible name', (level, name) => {
  renderAiQualityBadge(level)
  expect(screen.getByRole('img', { name })).toBeInTheDocument()
})

test('exposes no accessible badge when level is null', () => {
  renderAiQualityBadge(null)
  expect(screen.queryByRole('img', { name: /Data quality/ })).not.toBeInTheDocument()
})

test('exposes the info trigger as a button with an accessible name', () => {
  renderAiQualityBadge('high')
  expect(screen.getByRole('button', { name: 'Data quality information' })).toBeInTheDocument()
})
