/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import { defineComponent } from 'vue'

const submitHandler = vi.fn((e) => e.preventDefault())

beforeEach(() => {
  document.addEventListener('submit', submitHandler)
})

afterEach(() => {
  submitHandler.mockClear()
  document.removeEventListener('submit', submitHandler)
})

test('CmkIconButton does not submit form without click callback', async () => {
  const testComponent = defineComponent({
    components: { CmkIconButton },
    template: `
      <form>
        <CmkIconButton name="foo" />
      </form>
    `
  })
  render(testComponent)
  const button = screen.getByRole('button')
  await fireEvent.click(button)
  expect(submitHandler).not.toHaveBeenCalled()
})

test('CmkIconButton does not submit form with click callback', async () => {
  let clicked: boolean = false
  const testComponent = defineComponent({
    components: { CmkIconButton },
    setup() {
      const onclick = () => {
        clicked = true
      }
      return { onclick }
    },
    template: `
      <form>
        <CmkIconButton name="foo" @click="onclick" />
      </form>
    `
  })
  render(testComponent)
  const button = screen.getByRole('button')
  await fireEvent.click(button)
  expect(clicked).toBe(true)
  expect(submitHandler).not.toHaveBeenCalled()
})

test('CmkIconButton renders a themed image icon without a primary color', () => {
  const { container } = render(CmkIconButton, { props: { name: 'main-help' } })
  expect(container.querySelector('img.cmk-icon')).not.toBeNull()
  expect(container.querySelector('.cmk-multitone-icon')).toBeNull()
})

test('CmkIconButton renders a multitone icon for a primary color', () => {
  const { container } = render(CmkIconButton, {
    props: { name: 'more-actions', primaryColor: 'font' }
  })
  const icon = container.querySelector('.cmk-multitone-icon')
  expect(icon).not.toBeNull()
  expect(icon).toHaveClass('color-font')
  expect(container.querySelector('img.cmk-icon')).toBeNull()
})

test('CmkIconButton colors both tones of a two-color multitone icon', () => {
  const { container } = render(CmkIconButton, {
    props: { name: 'aggr', primaryColor: 'info', secondaryColor: 'warning' }
  })
  const icon = container.querySelector('.cmk-multitone-icon')
  expect(icon).toHaveClass('color-blue')
  expect(icon).toHaveClass('color-secondary-yellow')
})

// 'more-actions' has no themed bitmap behind it, so a raster render would resolve to no image at
// all. The prop types make that unreachable; this pins the rendering the types steer callers to.
test('CmkIconButton draws a multitone-only name as an inline SVG', () => {
  const { container } = render(CmkIconButton, {
    props: { name: 'more-actions', primaryColor: 'font' }
  })
  expect(container.querySelector('.cmk-multitone-icon svg')).not.toBeNull()
  expect(container.querySelector('img.cmk-icon')).toBeNull()
})
