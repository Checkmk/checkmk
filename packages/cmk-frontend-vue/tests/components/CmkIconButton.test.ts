/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable vue/one-component-per-file */
import { render, screen, fireEvent } from '@testing-library/vue'
import { defineComponent } from 'vue'
import CmkIconButton from '@/components/CmkIconButton.vue'

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
