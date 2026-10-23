/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import UclNavPage from '@ucl/_ucl/components/UclNavPage.vue'
import type { NavPage } from '@ucl/_ucl/composables/useNavigation'
import { test } from 'vitest'
import { defineComponent } from 'vue'

test('shows the status chip next to the page name', () => {
  const page: NavPage = {
    type: 'page',
    name: 'CmkFoo',
    path: '/components/cmk-foo',
    component: defineComponent({
      props: { screenshotMode: { type: Boolean, required: true } },
      template: '<div/>'
    }),
    status: 'new'
  }

  render(UclNavPage, {
    props: { page },
    global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } }
  })

  screen.getByText('CmkFoo')
  screen.getByText('New')
})
