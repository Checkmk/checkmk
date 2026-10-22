/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { afterEach, describe, expect, it, vi } from 'vitest'

import DrillUpButton from '@/page-header/DrillUpButton.vue'

function withHistory(length: number) {
  vi.spyOn(History.prototype, 'length', 'get').mockReturnValue(length)
}

function referredBy(url: string) {
  vi.spyOn(Document.prototype, 'referrer', 'get').mockReturnValue(url)
}

describe('DrillUpButton', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('goes back in the history of the tab', async () => {
    withHistory(2)
    const back = vi.spyOn(History.prototype, 'back').mockImplementation(() => {})
    render(DrillUpButton, { props: { title: 'Overview' } })

    await userEvent.click(screen.getByRole('button', { name: 'Back to Overview' }))

    expect(back).toHaveBeenCalledOnce()
  })

  it('shows no button without history and referrer', () => {
    withHistory(1)
    referredBy('')

    render(DrillUpButton, { props: { title: 'Overview' } })

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
