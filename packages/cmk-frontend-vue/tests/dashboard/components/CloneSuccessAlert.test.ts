/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import CloneSuccessAlert from '@/dashboard/components/CloneSuccessAlert.vue'

function renderAlert(props: { clonedAsResponsive?: boolean } = {}) {
  return render(CloneSuccessAlert, { props: { open: true, ...props } })
}

async function letAutoDismissalElapse(): Promise<void> {
  vi.runAllTimers()
  await nextTick()
}

describe('CloneSuccessAlert', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('closes by itself after a plain clone', async () => {
    renderAlert()

    await letAutoDismissalElapse()

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('stays open after cloning an anchored dashboard as responsive', async () => {
    renderAlert({ clonedAsResponsive: true })

    await letAutoDismissalElapse()

    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('asks to review the layout after cloning as responsive', () => {
    renderAlert({ clonedAsResponsive: true })

    expect(
      screen.getByText('Review the layout and adjust any shifted or resized widgets if needed.')
    ).toBeInTheDocument()
  })
})
