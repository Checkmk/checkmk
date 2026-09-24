/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import CmkPointerTooltip from 'cmk-ui-library/components/CmkPointerTooltip.vue'
import { h, nextTick } from 'vue'

const tooltip = (): HTMLElement | null => document.querySelector('.cmk-pointer-tooltip')

function renderTooltip(pointer: { clientX: number; clientY: number } | null) {
  return render(CmkPointerTooltip, {
    props: { pointer },
    slots: { default: () => h('span', 'Tooltip content') }
  })
}

describe('CmkPointerTooltip', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders its slot beside the pointer', () => {
    renderTooltip({ clientX: 105, clientY: 205 })

    expect(screen.getByText('Tooltip content')).toBeInTheDocument()
    // jsdom reports a zero-size element, so the position is the pointer plus the offset; the
    // flip and the clamp are covered by the computeTooltipPosition tests.
    expect(tooltip()!.style.left).toBe('124px')
    expect(tooltip()!.style.top).toBe('213px')
  })

  it('renders nothing without a pointer', () => {
    renderTooltip(null)

    expect(tooltip()).toBeNull()
  })

  it('keeps its scoped-style attribute when teleported to the body', () => {
    renderTooltip({ clientX: 0, clientY: 0 })

    expect(tooltip()!.parentElement).toBe(document.body)
    const attributeNames = Array.from(tooltip()!.attributes).map((attribute) => attribute.name)
    expect(attributeNames.some((name) => name.startsWith('data-v-'))).toBe(true)
  })

  it('opens as a manual popover', async () => {
    const showPopover = vi.spyOn(HTMLElement.prototype, 'showPopover')

    renderTooltip({ clientX: 0, clientY: 0 })
    await nextTick()

    expect(tooltip()!.getAttribute('popover')).toBe('manual')
    expect(showPopover).toHaveBeenCalledOnce()
  })

  it('asks to be dismissed when the page scrolls', () => {
    const { emitted } = renderTooltip({ clientX: 0, clientY: 0 })

    window.dispatchEvent(new Event('scroll'))

    expect(emitted('dismiss')).toHaveLength(1)
  })

  it('asks to be dismissed when the window resizes', () => {
    const { emitted } = renderTooltip({ clientX: 0, clientY: 0 })

    window.dispatchEvent(new Event('resize'))

    expect(emitted('dismiss')).toHaveLength(1)
  })
})
