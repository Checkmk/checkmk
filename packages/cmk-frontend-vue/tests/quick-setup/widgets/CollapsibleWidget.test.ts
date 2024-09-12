/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import CollapsibleWidget from '@/quick-setup/widgets/CollapsibleWidget.vue'
import { render, screen } from '@testing-library/vue'

test('CollapsibleWidget renders values and label', async () => {
  render(CollapsibleWidget, {
    props: {
      open: true,
      title: 'I am a label',
      items: [
        { widget_type: 'text', text: 'Welcome' },
        { widget_type: 'text', text: 'to Jurassic Park' }
      ]
    }
  })

  expect(screen.queryByText('I am a label')).toBeTruthy()
  expect(screen.queryByText('Welcome')).toBeTruthy()
  expect(screen.queryByText('to Jurassic Park')).toBeTruthy()
})
