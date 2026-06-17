/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'

import GhostWidth from '@/components/date-time/private/display/GhostWidth.vue'

describe('GhostWidth', () => {
  test('renders one hidden ghost span per variant plus the slot', () => {
    const { container } = render(GhostWidth, {
      props: { variants: ['AM', 'PM'] },
      slots: { default: '<span class="slot">Hi</span>' }
    })
    const ghosts = Array.from(container.querySelectorAll<HTMLElement>('.cmk-ghost-width__ghost'))
    expect(ghosts).toHaveLength(2)
    expect(ghosts.map((ghost) => ghost.textContent)).toEqual(['AM', 'PM'])
    ghosts.forEach((ghost) => expect(ghost).toHaveAttribute('aria-hidden', 'true'))
    expect(container.querySelector('.slot')).toBeInTheDocument()
  })

  test('empty variants render no ghosts', () => {
    const { container } = render(GhostWidth, {
      props: { variants: [] },
      slots: { default: '<span class="slot">Hi</span>' }
    })
    expect(container.querySelectorAll('.cmk-ghost-width__ghost')).toHaveLength(0)
    expect(container.querySelector('.slot')).toBeInTheDocument()
  })
})
