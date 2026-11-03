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
import type { CmkMenuItem } from 'cmk-ui-library/components/CmkMenu'

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
  ['Interface eth0', 'Bandwidth in'],
  ['Filesystem /var', 'Used space']
]

const ITEM_COUNTS = { few: 5, many: 12 }

const DEMO_ITEMS: CmkMenuItem[] = HOSTS.map((host, index) => {
  const [service, metric] = SERVICES[index % SERVICES.length]!
  const links: CmkMenuItem['links'] =
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
      { text: metric, bold: true }
    ],
    links
  }
})

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
    description: 'Follows the focused link, or opens the submenu of the focused item.'
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
} satisfies PanelConfigFor<typeof CmkMenu, 'items'> & PanelConfig
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
import { computed } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkMenu, 'items'>().createRef(panelConfig)

const items = computed(() => DEMO_ITEMS.slice(0, ITEM_COUNTS[propState.value.itemCount]))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkMenu</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkMenu :items="items" :label="propState.label" :searchable="propState.searchable" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
