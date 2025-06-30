/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import CmkAccordion from '@/components/CmkAccordion/CmkAccordion.vue'
import CmkAccordionItem from '@/components/CmkAccordion/CmkAccordionItem.vue'
import { screen, render } from '@testing-library/vue'
import { type Ref, defineComponent, ref } from 'vue'

const createAccordionComponent = (
  items: number,
  min: number,
  max: number,
  opened: Ref<string[]>
) => {
  let itemsTemplate = ''
  for (let i = 0; i < items; i++) {
    itemsTemplate += `<CmkAccordionItem
      value="item-${i + 1}"
      :disabled="${i + 1 === 3}"
    >
      <template #header>
        <h2>
          Title of item-${i + 1}
        </h2>
      </template>
      <template #content>
       Content of item-${i + 1}
      </template>
    </CmkAccordionItem>`
  }

  return defineComponent({
    components: { CmkAccordion, CmkAccordionItem },
    setup() {
      return { opened }
    },
    template: `
    <CmkAccordion
    v-model="opened"
    :max-open="parseInt(${max})"
    :min-open="parseInt(${min})"
  >
    ${itemsTemplate}
  </CmkAccordion>
`
  })
}

const checkAccordionState = async (
  receivedOpen: string[],
  expectedOpen: string[],
  expectedClosed: string[] = []
): Promise<void> => {
  expect(receivedOpen.length).toBe(expectedOpen.length)

  for (const [index, key] of receivedOpen.entries()) {
    expect(expectedOpen.indexOf(key)).toBe(index) // check for existence and corecct order
    expect(expectedClosed).not.toContain(key)

    const node = (await screen.findByText(`Content of ${key}`)).parentElement
    expect(node).toHaveAttribute('data-state', 'open')
  }

  for (const key of expectedClosed.entries()) {
    expect(screen.queryByText(`Content of ${key}`)).toBeNull()
  }
}

test('Accordion wich opens min and max 1 item at a time', async () => {
  const opened = ref<string[]>(['item-1'])
  render(createAccordionComponent(4, 1, 1, opened))

  const accTrigger2 = screen.getByRole('button', { name: `Open accordion item item-2` })

  accTrigger2.click() // open item-2 => item-1 should be closed

  await checkAccordionState(opened.value, ['item-2'], ['item-1', 'item-3', 'item-4'])
})

test('Accordion wich opens max 1 items at a time and all items can be closed', async () => {
  const opened = ref<string[]>(['item-1'])
  render(createAccordionComponent(4, 0, 1, opened))

  const accTrigger2 = screen.getByRole('button', { name: `Open accordion item item-2` })

  await accTrigger2.click() // open item-2
  await checkAccordionState(opened.value, ['item-2'], ['item-1', 'item-3', 'item-4'])

  await accTrigger2.click() // close item-2
  await checkAccordionState(opened.value, [], ['item-1', 'item-2', 'item-3', 'item-4'])
})

test('Accordion wich opens max 2 items at a time and all items can be closed', async () => {
  const opened = ref<string[]>(['item-1'])
  render(createAccordionComponent(4, 0, 2, opened))

  const accTrigger2 = screen.getByRole('button', { name: `Open accordion item item-2` })
  const accTrigger4 = screen.getByRole('button', { name: `Open accordion item item-4` })

  await accTrigger2.click() // open item-2
  await accTrigger4.click() // open item-4 => should close item-1

  await checkAccordionState(opened.value, ['item-2', 'item-4'], ['item-1', 'item-3'])

  await accTrigger2.click() // close item-2
  await accTrigger4.click() // close item-4
  await checkAccordionState(opened.value, [], ['item-1', 'item-2', 'item-3', 'item-4'])
})

test('Accordion wich opens all items at a time and at least 2 items have to be opened', async () => {
  const opened = ref<string[]>(['item-1', 'item-4'])
  render(createAccordionComponent(4, 2, 0, opened))
  await checkAccordionState(opened.value, ['item-1', 'item-4'], ['item-2', 'item-3'])

  const accTrigger2 = screen.getByRole('button', { name: `Open accordion item item-2` })
  const accTrigger4 = screen.getByRole('button', { name: `Open accordion item item-4` })

  await accTrigger2.click() // open item 2
  await checkAccordionState(opened.value, ['item-1', 'item-4', 'item-2'], ['item-3'])

  await accTrigger4.click() // close item 4
  await checkAccordionState(opened.value, ['item-1', 'item-2'], ['item-3', 'item-4'])

  await accTrigger2.click() // close item 2  => should be ignored
  await checkAccordionState(opened.value, ['item-1', 'item-2'], ['item-3', 'item-4'])
})

test('Accordion wich ignores disabled item', async () => {
  const opened = ref<string[]>(['item-1'])
  render(createAccordionComponent(4, 1, 1, opened))

  const accTrigger3 = screen.getByRole('button', { name: `Open accordion item item-3` })

  await accTrigger3.click() // open item-3 => disabled, should be ignored

  await checkAccordionState(opened.value, ['item-1'], ['item-2', 'item-3', 'item-4'])
})
