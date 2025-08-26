/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { defineComponent } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

test('CmkCheckbox can be appended with standard props', async () => {
  render(
    defineComponent({
      components: { CmkCheckbox },
      template: `
          <CmkCheckbox role='option'/>
      `
    })
  )

  await screen.findByRole('option')
})

test('CmkCheckbox sets aria-checked', async () => {
  render(CmkCheckbox, {
    props: {
      modelValue: true
    }
  })

  screen.getByRole('checkbox', { checked: true })
})

test('CmkCheckbox renders updated validation', async () => {
  const { rerender } = render(CmkCheckbox, {
    props: {
      modelValue: false,
      externalErrors: ['some old validation']
    }
  })

  await rerender({
    modelValue: false,
    externalErrors: ['some new validation']
  })

  await screen.findByText('some new validation')
})
