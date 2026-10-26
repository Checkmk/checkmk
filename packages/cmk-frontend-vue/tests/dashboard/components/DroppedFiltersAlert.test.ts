/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DroppedFiltersAlert from '@/dashboard/components/DroppedFiltersAlert.vue'

describe('DroppedFiltersAlert', () => {
  it('reports its dismissal by the close button', async () => {
    const { emitted } = render(DroppedFiltersAlert, {
      props: { warning: 'Host labels (os): the clicked object lacks the configured key' }
    })

    await userEvent.click(screen.getByRole('button', { name: 'Close' }))

    expect(emitted('dismiss')).toHaveLength(1)
  })
})
