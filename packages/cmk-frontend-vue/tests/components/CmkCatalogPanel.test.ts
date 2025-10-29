/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent } from 'vue'

import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'

const submitHandler = vi.fn((e) => e.preventDefault())

beforeEach(() => {
  document.addEventListener('submit', submitHandler)
})

afterEach(() => {
  submitHandler.mockClear()
  document.removeEventListener('submit', submitHandler)
})

test('catalog panel shows content', async () => {
  render(CmkCatalogPanel, {
    props: {
      title: 'Catalog Panel Title'
    },
    slots: {
      default: '<div>Some content</div>'
    }
  })

  await screen.findByText('Some content')
})

test('catalog panel hides content on click', async () => {
  render(CmkCatalogPanel, {
    props: {
      title: 'Catalog Panel Title'
    },
    slots: {
      default: '<div>Some content</div>'
    }
  })

  // Sync barrier
  await screen.findByText('Some content')

  const header = screen.getByRole('button', { name: 'Toggle Catalog Panel Title' })
  await userEvent.click(header)

  expect(await screen.queryByText('Some content')).not.toBeVisible()
})

test('catalog panel does not submit form on toggle', async () => {
  const testComponent = defineComponent({
    components: { CmkCatalogPanel },
    template: `
      <form>
        <CmkCatalogPanel title="foo" />
      </form>
    `
  })
  render(testComponent)

  const header = screen.getByRole('button', { name: 'Toggle foo' })
  await userEvent.click(header)

  expect(submitHandler).not.toHaveBeenCalled()
})
