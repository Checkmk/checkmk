/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'

import RateLimitContent from '@/ai/components/conversation/content/RateLimitContent.vue'

function renderRateLimitContent() {
  return render(RateLimitContent, {
    props: {
      content_type: 'rate_limit'
    },
    global: {
      stubs: {
        CmkIcon: true,
        CmkButton: {
          template: '<button type="button"><slot /></button>'
        }
      }
    }
  })
}

test('emits done on mount', () => {
  const { emitted } = renderRateLimitContent()

  expect(emitted('done')).toHaveLength(1)
})

test('renders the title and message', () => {
  renderRateLimitContent()

  expect(screen.getByText('Feature temporarily unavailable')).toBeInTheDocument()
  expect(
    screen.getByText('We are currently experiencing high load. Please try again later.')
  ).toBeInTheDocument()
})

test('emits close when the Close button is clicked', async () => {
  const { emitted } = renderRateLimitContent()

  await fireEvent.click(screen.getByText('Close'))

  expect(emitted('close')).toHaveLength(1)
})
