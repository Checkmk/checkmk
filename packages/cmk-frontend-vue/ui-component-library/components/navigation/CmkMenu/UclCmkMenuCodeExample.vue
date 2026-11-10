<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkMenu, { type CmkMenuCategory, type CmkMenuItem } from 'cmk-ui-library/components/CmkMenu'
import { ref } from 'vue'

const items: CmkMenuItem[] = [
  {
    color: '#3cc2ff',
    label: [
      { text: 'web01', truncateOrder: 1 },
      { text: 'CPU load', truncateOrder: 2 },
      { text: 'Load average 1', bold: true, truncateOrder: 3, line: 2 }
    ],
    links: [{ title: 'Host status', url: 'view.py?view_name=host&host=web01' }]
  },
  {
    color: '#8c7cff',
    label: [
      { text: 'db01', truncateOrder: 1 },
      { text: 'Memory', truncateOrder: 2 },
      { text: 'RAM used', bold: true, truncateOrder: 3, line: 2 }
    ],
    links: [
      { title: 'Host status', url: 'view.py?view_name=host&host=db01' },
      { title: 'Service status', url: 'view.py?view_name=service&host=db01&service=Memory' }
    ]
  }
]

// Value items emit `select` instead of navigating.
const graphs: CmkMenuItem[] = [
  { label: [{ text: 'Custom graph 1' }], value: 'custom_graph_1', icon: 'clone' },
  { label: [{ text: 'Custom graph 2' }], value: 'custom_graph_2', icon: 'clone' }
]
const picked = ref<string | null>(null)

// Categories add a toggle below the search and head their items; a field shows the pick.
const categories: CmkMenuCategory[] = [
  { value: 'dashboards', title: 'Dashboard' },
  { value: 'views', title: 'View' }
]
const targets: CmkMenuItem[] = [
  {
    label: [{ text: 'Main dashboard' }],
    value: 'main',
    category: 'dashboards',
    detail: 'Built-in'
  },
  { label: [{ text: 'All hosts' }], value: 'allhosts', category: 'views', detail: 'Built-in' }
]
const target = ref<string | null>(null)
</script>

<template>
  <CmkMenu :items="items" label="Contextual links" />

  <CmkMenu
    :items="graphs"
    label="Clone custom graph"
    trigger-icon="clone"
    trigger-text="Clone custom graph"
    search-placeholder="Search custom graphs ..."
    searchable
    @select="(value) => (picked = value)"
  />

  <CmkMenu
    :items="targets"
    :categories="categories"
    label="Target page"
    trigger-variant="field"
    :trigger-text="targets.find((item) => 'value' in item && item.value === target)?.label[0]?.text"
    searchable
    @select="(value) => (target = value)"
  />
</template>
