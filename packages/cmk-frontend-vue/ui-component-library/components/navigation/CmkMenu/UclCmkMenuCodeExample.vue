<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkMenu, { type CmkMenuItem } from 'cmk-ui-library/components/CmkMenu'

const items: CmkMenuItem[] = [
  {
    color: '#3cc2ff',
    label: [
      { text: 'web01', truncateOrder: 1 },
      { text: 'CPU load', truncateOrder: 2 },
      { text: 'Load average 1', bold: true }
    ],
    links: [{ title: 'Host status', url: 'view.py?view_name=host&host=web01' }]
  },
  {
    color: '#8c7cff',
    label: [
      { text: 'db01', truncateOrder: 1 },
      { text: 'Memory', truncateOrder: 2 },
      { text: 'RAM used', bold: true }
    ],
    links: [
      { title: 'Host status', url: 'view.py?view_name=host&host=db01' },
      { title: 'Service status', url: 'view.py?view_name=service&host=db01&service=Memory' }
    ]
  }
]
</script>

<template>
  <CmkMenu :items="items" label="Contextual links" />
</template>
