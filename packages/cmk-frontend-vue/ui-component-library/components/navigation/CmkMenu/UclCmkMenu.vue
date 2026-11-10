<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import {
  type PanelConfig,
  type PanelConfigFor,
  listOptions
} from '@ucl/_ucl/components/detail-page'
import type {
  CmkMenuCategory,
  CmkMenuItem,
  CmkMenuLinkItem
} from 'cmk-ui-library/components/CmkMenu'

import codeExample from './UclCmkMenuCodeExample.vue?raw'

const COLORS = [
  '#3cc2ff',
  '#8c7cff',
  '#e3388e',
  '#5bae9a',
  '#ffa95e',
  '#ffd24f',
  '#47a3f6',
  '#7ef0d0',
  '#ff8c8c'
]

const HOSTS = [
  'web01',
  'db-cluster-node-03.production.eu-central.example.com',
  'mail',
  'backup-storage-02',
  'proxy',
  'build-agent-07',
  'dns01',
  'fileserver',
  'monitoring',
  'gateway',
  'ldap02',
  'printer-floor-3'
]

const SERVICES: [string, string][] = [
  ['CPU load', 'Load average 1'],
  ['Memory', 'RAM used'],
  ['Interface eth0', 'Bandwidth in, averaged over the last fifteen minutes'],
  ['Filesystem /var', 'Used space']
]

const ITEM_COUNTS = { few: 5, many: 12 }

const ITEM_KINDS = {
  links: 'Links, one line',
  twoLineLinks: 'Links, two lines',
  mixedLinks: 'Links, mixed lines',
  values: 'Values',
  categorised: 'Values in categories'
}

const TRIGGER_VARIANTS = { button: 'Button', field: 'Field' }

const DEMO_CATEGORIES: CmkMenuCategory[] = [
  { value: 'dashboards', title: 'Dashboard' },
  { value: 'views', title: 'View' }
]

const DEMO_ITEMS: CmkMenuItem[] = HOSTS.map((host, index) => {
  const [service, metric] = SERVICES[index % SERVICES.length]!
  const links: CmkMenuLinkItem['links'] =
    index % 3 === 2
      ? [{ title: 'Host status', url: '#' }]
      : [
          { title: 'Host status', url: '#' },
          { title: 'Service status', url: '#' },
          { title: 'Service performance graphs of the last 25 hours', url: '#' }
        ]
  return {
    color: COLORS[index % COLORS.length]!,
    label: [
      { text: host, truncateOrder: 1 },
      { text: service, truncateOrder: 2 },
      { text: metric, bold: true, truncateOrder: 3 }
    ],
    links
  }
})

// The bold metric moves to line 2, below host and service.
const DEMO_TWO_LINE_ITEMS: CmkMenuItem[] = DEMO_ITEMS.map((item) => ({
  ...item,
  label: item.label.map((part) => (part.bold ? { ...part, line: 2 as const } : part))
}))

const DEMO_MIXED_ITEMS: CmkMenuItem[] = DEMO_ITEMS.map((item, index) =>
  index % 2 === 0 ? DEMO_TWO_LINE_ITEMS[index]! : item
)

const DEMO_VALUE_ITEMS: CmkMenuItem[] = HOSTS.map((_, index) => ({
  label: [{ text: `Custom graph ${index + 1}` }],
  value: `custom_graph_${index + 1}`,
  icon: 'clone'
}))

// Every third item is a view, every second one built-in, as in a picker of link targets.
const DEMO_CATEGORISED_ITEMS: CmkMenuItem[] = HOSTS.map((host, index) => ({
  label: [{ text: `Overview of ${host}`, truncateOrder: 1 }],
  value: host,
  category: index % 3 === 2 ? 'views' : 'dashboards',
  detail: index % 2 === 0 ? 'Built-in' : 'Custom'
}))

const DEMO_ITEMS_BY_KIND: Record<keyof typeof ITEM_KINDS, CmkMenuItem[]> = {
  links: DEMO_ITEMS,
  twoLineLinks: DEMO_TWO_LINE_ITEMS,
  mixedLinks: DEMO_MIXED_ITEMS,
  values: DEMO_VALUE_ITEMS,
  categorised: DEMO_CATEGORISED_ITEMS
}

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the trigger.'
  },
  {
    keys: ['Enter', 'Space', 'ArrowDown'],
    description:
      'Opens the menu from the trigger. With search shown, focus starts in the search field.'
  },
  {
    keys: ['Tab', 'Shift+Tab'],
    description:
      'With categories, moves between the search field and the buttons of the category toggle; Enter or Space picks the focused category.'
  },
  {
    keys: ['ArrowDown', 'ArrowUp'],
    description:
      'Moves between the items. From the search field, ArrowDown moves to the first item.'
  },
  {
    keys: ['ArrowRight'],
    description: 'Opens the submenu of an item with several links and focuses its first link.'
  },
  {
    keys: ['ArrowLeft'],
    description: 'Closes the submenu and returns focus to its item.'
  },
  {
    keys: ['Enter'],
    description:
      'Follows the focused link, selects the focused value, or opens the submenu of the focused item.'
  },
  {
    keys: ['Escape'],
    description: 'Closes the menu and returns focus to the trigger.'
  }
]

export const panelConfig = {
  label: {
    type: 'string' as const,
    title: 'Accessible name',
    initialState: 'Contextual links'
  },
  searchable: {
    type: 'boolean' as const,
    title: 'Searchable',
    initialState: false,
    help: 'Search is always shown from nine items on.'
  },
  itemKind: {
    type: 'list' as const,
    title: 'Item kind',
    options: listOptions<keyof typeof ITEM_KINDS>(ITEM_KINDS),
    initialState: 'links' as const,
    help: 'Links navigate (metric inline, on a second line, or mixed); values are emitted with select, e.g. to pick a graph. Values in categories add the category toggle, headings and a detail per item.'
  },
  triggerVariant: {
    type: 'list' as const,
    title: 'Trigger variant',
    options: listOptions<keyof typeof TRIGGER_VARIANTS>(TRIGGER_VARIANTS),
    initialState: 'button' as const,
    help: 'A field fills its container like a dropdown, showing the trigger text or else the accessible name.'
  },
  triggerText: {
    type: 'string' as const,
    title: 'Trigger text',
    initialState: '',
    help: 'Without text, the trigger is icon-only.'
  },
  searchPlaceholder: {
    type: 'string' as const,
    title: 'Search placeholder',
    initialState: ''
  },
  itemCount: {
    type: 'list' as const,
    title: 'Items',
    options: listOptions<keyof typeof ITEM_COUNTS>({
      few: '5 items',
      many: '12 items'
    }),
    initialState: 'few' as const,
    help: 'Up to nine items the list grows with them; beyond that it scrolls at a fixed height.'
  }
} satisfies PanelConfigFor<typeof CmkMenu, 'items' | 'triggerIcon' | 'categories'> & PanelConfig
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import CmkMenu from 'cmk-ui-library/components/CmkMenu'
import { computed, ref, watch } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkMenu,
  'items' | 'triggerIcon' | 'categories'
>().createRef(panelConfig)

const pickValues = computed(() => ['values', 'categorised'].includes(propState.value.itemKind))
const categorised = computed(() => propState.value.itemKind === 'categorised')
// Each item kind starts with the trigger it has in use: text for picking values, icon-only for
// links, and a field for picking from categories.
watch(
  () => propState.value.itemKind,
  (kind) => {
    propState.value.triggerText = kind === 'values' ? 'Clone custom graph' : ''
    propState.value.triggerVariant = kind === 'categorised' ? 'field' : 'button'
  }
)
const items = computed(() =>
  DEMO_ITEMS_BY_KIND[propState.value.itemKind].slice(0, ITEM_COUNTS[propState.value.itemCount])
)
const selected = ref<string | null>(null)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkMenu</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-cmk-menu">
        <CmkMenu
          :items="items"
          :label="propState.label"
          :searchable="propState.searchable"
          :trigger-icon="propState.itemKind === 'values' ? 'clone' : undefined"
          :trigger-text="propState.triggerText || undefined"
          :trigger-variant="propState.triggerVariant"
          :categories="categorised ? DEMO_CATEGORIES : undefined"
          :search-placeholder="propState.searchPlaceholder || undefined"
          @select="(value) => (selected = value)"
        />
        <p v-if="pickValues">Selected: {{ selected ?? '–' }}</p>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-cmk-menu {
  display: flex;
  width: 320px;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--dimension-6);

  > p {
    margin: 0;
  }
}
</style>
