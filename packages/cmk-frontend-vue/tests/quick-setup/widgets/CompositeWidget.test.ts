/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import CompositeWidget from '@/quick-setup/components/quick-setup/widgets/CompositeWidget.vue'
import { getWidget } from '@/quick-setup/components/quick-setup/widgets/utils'
import { quickSetupGetWidgetKey } from '@/quick-setup/components/quick-setup/utils'
import { render, screen } from '@testing-library/vue'

test('CompositeWidget renders values and label', async () => {
  render(CompositeWidget, {
    global: {
      provide: {
        [quickSetupGetWidgetKey]: getWidget
      }
    },
    props: {
      items: [
        { widget_type: 'text', text: 'Welcome' },
        { widget_type: 'text', text: 'to Jurassic Park' }
      ]
    }
  })

  expect(screen.queryByText('Welcome')).toBeTruthy()
  expect(screen.queryByText('to Jurassic Park')).toBeTruthy()
})
