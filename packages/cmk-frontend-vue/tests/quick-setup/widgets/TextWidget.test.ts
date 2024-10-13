/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import TextWidget from '@/quick-setup/components/quick-setup/widgets/TextWidget.vue'

test('TextWidget renders value', async () => {
  render(TextWidget, {
    props: {
      text: 'Hello World'
    }
  })

  expect(screen.queryByText('Hello World')).toBeTruthy()
})
