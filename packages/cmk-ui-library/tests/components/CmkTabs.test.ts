/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import CmkTabs, { CmkTab, CmkTabContent } from 'cmk-ui-library/components/CmkTabs'
import { defineComponent, onMounted, ref } from 'vue'

/** Counts its own mounts and holds state no prop feeds back in, so a remount is observable. */
function tabBody(onMount: () => void) {
  return defineComponent({
    setup() {
      const clicks = ref(0)
      onMounted(onMount)
      return { clicks }
    },
    template: `<button data-testid="counter" @click="clicks += 1">{{ clicks }}</button>`
  })
}

function renderTabs(tabsProps: Record<string, unknown>, onMount: () => void) {
  const harness = defineComponent({
    components: { CmkTabs, CmkTab, CmkTabContent, TabBody: tabBody(onMount) },
    props: { tabsProps: { type: Object, required: true } },
    setup: () => ({ active: ref('tab-1') }),
    template: `
      <CmkTabs v-model="active" v-bind="tabsProps">
        <template #tabs>
          <CmkTab id="tab-1">First</CmkTab>
          <CmkTab id="tab-2">Second</CmkTab>
        </template>
        <template #tab-contents>
          <CmkTabContent id="tab-1"><TabBody /></CmkTabContent>
          <CmkTabContent id="tab-2">Second panel</CmkTabContent>
        </template>
      </CmkTabs>`
  })
  return render(harness, { props: { tabsProps } })
}

async function openTab(name: string): Promise<void> {
  await userEvent.click(screen.getByRole('tab', { name }))
}

test('drops the content of a hidden panel by default', async () => {
  const mount = vi.fn()
  renderTabs({}, mount)

  await userEvent.click(screen.getByTestId('counter'))
  expect(screen.getByTestId('counter')).toHaveTextContent('1')

  await openTab('Second')
  expect(screen.queryByTestId('counter')).not.toBeInTheDocument()

  await openTab('First')
  expect(screen.getByTestId('counter')).toHaveTextContent('0')
  expect(mount).toHaveBeenCalledTimes(2)
})

test('keeps a hidden panel mounted when unmountOnHide is off', async () => {
  const mount = vi.fn()
  renderTabs({ unmountOnHide: false }, mount)

  await userEvent.click(screen.getByTestId('counter'))
  expect(screen.getByTestId('counter')).toHaveTextContent('1')

  await openTab('Second')
  const hiddenCounter = screen.getByTestId('counter')
  expect(hiddenCounter.closest('[role="tabpanel"]')).toHaveAttribute('hidden')

  await openTab('First')
  expect(screen.getByTestId('counter')).toHaveTextContent('1')
  expect(mount).toHaveBeenCalledTimes(1)
})
