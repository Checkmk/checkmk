/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { render, screen } from '@testing-library/vue'
import NoteTextWidget from '@/quick-setup/components/quick-setup/widgets/NoteTextWidget.vue'

test('NoteTextWidget renders value', async () => {
  render(NoteTextWidget, {
    props: {
      text: 'Hello World'
    }
  })

  expect(screen.queryByText('Hello World')).toBeTruthy()
})
