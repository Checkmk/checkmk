/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { defineComponent } from 'vue'

import CmkHeading from '@/components/typography/CmkHeading.vue'

test('CmkHeading triggers onclick handler', async () => {
  let clicked = false
  render(
    defineComponent({
      components: { CmkHeading },
      methods: {
        handleClick() {
          clicked = true
        }
      },
      template: `<CmkHeading @click="handleClick">Clickable Heading</CmkHeading>`
    })
  )

  const heading = screen.getByText('Clickable Heading')

  await heading.click()

  expect(clicked).toBe(true)
})
