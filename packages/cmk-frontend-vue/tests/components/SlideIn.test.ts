/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { mount } from '@vue/test-utils'
import SlideIn from '@/components/SlideIn.vue'
import { findByText, queryByText, waitForElementToBeRemoved } from '@testing-library/vue'

test('Slidein shows and hides content', async () => {
  document.body.innerHTML = ''
  const wrapper = mount(SlideIn, {
    slots: {
      default: '<div id="main">Main Content</div>'
    },
    attachTo: document.body,
    props: {
      open: true,
      header: {
        title: 'asd',
        closeButton: true
      }
    }
  })

  await findByText(document.body, 'Main Content')

  await wrapper.setProps({ open: false })

  await waitForElementToBeRemoved(() => queryByText(document.body, 'Main Content'))
})
