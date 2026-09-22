/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import { defineComponent } from 'vue'

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

test('a non-collapsible catalog panel shows its content without a toggle', async () => {
  render(CmkCatalogPanel, {
    props: {
      title: 'Duration',
      collapsible: false
    },
    slots: {
      default: '<div>Some content</div>'
    }
  })

  await screen.findByText('Some content')

  expect(screen.queryByRole('button', { name: 'Toggle Duration' })).toBeNull()
})

test('clicking a non-collapsible header leaves the content shown', async () => {
  render(CmkCatalogPanel, {
    props: {
      title: 'Duration',
      collapsible: false
    },
    slots: {
      default: '<div>Some content</div>'
    }
  })

  await userEvent.click(await screen.findByText('Duration'))

  expect(screen.getByText('Some content')).toBeVisible()
})

test('a panel turned non-collapsible reopens its closed content', async () => {
  const view = render(CmkCatalogPanel, {
    props: {
      title: 'Duration',
      open: false,
      collapsible: true
    },
    slots: {
      default: '<div>Some content</div>'
    }
  })

  expect(screen.queryByText('Some content')).not.toBeVisible()

  await view.rerender({ title: 'Duration', open: false, collapsible: false })

  expect(screen.getByText('Some content')).toBeVisible()
})
