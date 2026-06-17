/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'

import FieldBox from '@/components/date-time/private/input/FieldBox.vue'

describe('FieldBox', () => {
  test('open adds the open modifier class', () => {
    const { container } = render(FieldBox, { props: { open: true } })
    expect(container.firstElementChild).toHaveClass('cmk-field-box--open')
  })

  test('disabled adds the disabled modifier class', () => {
    const { container } = render(FieldBox, { props: { disabled: true } })
    expect(container.firstElementChild).toHaveClass('cmk-field-box--disabled')
  })
})
