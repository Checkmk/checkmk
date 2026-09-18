/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'

import PinHandle from '@/graphing/components/TimeSeriesGraph/overlay/PinHandle.vue'

describe('PinHandle', () => {
  test('the add variant is a labeled button carrying the unpinned marker', () => {
    const { container } = render(PinHandle, { props: { variant: 'add' } })

    expect(screen.getByRole('button', { name: 'Add pin' })).toBeInTheDocument()
    expect(container.querySelector('.graphing-pin-handle--add')).toBeInTheDocument()
  })

  test('the remove variant is a labeled button carrying the pinned marker', () => {
    const { container } = render(PinHandle, { props: { variant: 'remove' } })

    expect(screen.getByRole('button', { name: 'Remove pin' })).toBeInTheDocument()
    expect(container.querySelector('.graphing-pin-handle--remove')).toBeInTheDocument()
  })

  // Body and outline are separate elements so the variant can colour each of them.
  test('both variants draw the same marker', () => {
    const add = render(PinHandle, { props: { variant: 'add' } }).container
    const remove = render(PinHandle, { props: { variant: 'remove' } }).container

    const shapeOf = (root: Element, part: string): string | null | undefined =>
      root.querySelector(`.graphing-pin-handle__${part}`)?.getAttribute('d')
    expect(shapeOf(add, 'body')).toBeTruthy()
    expect(shapeOf(add, 'outline')).toBeTruthy()
    expect(shapeOf(remove, 'body')).toBe(shapeOf(add, 'body'))
    expect(shapeOf(remove, 'outline')).toBe(shapeOf(add, 'outline'))
  })

  // A pin plus a hover puts two handles on one graph. Mounting both in one app is what makes
  // the exported ids collide if they are not rewritten.
  test('each instance masks through an id of its own', () => {
    const { container } = render({
      components: { PinHandle },
      template: '<div><PinHandle variant="add" /><PinHandle variant="remove" /></div>'
    })

    const masks = Array.from(container.querySelectorAll('mask')).map((mask) => mask.id)
    expect(masks).toHaveLength(2)
    expect(new Set(masks).size).toBe(2)
    Array.from(container.querySelectorAll('.graphing-pin-handle__outline')).forEach(
      (outline, index) => {
        expect(outline.getAttribute('mask')).toBe(`url(#${masks[index]})`)
      }
    )
  })

  test('a click emits action', async () => {
    const { emitted } = render(PinHandle, { props: { variant: 'remove' } })

    await fireEvent.click(screen.getByRole('button', { name: 'Remove pin' }))

    expect(emitted()).toHaveProperty('action')
  })
})
