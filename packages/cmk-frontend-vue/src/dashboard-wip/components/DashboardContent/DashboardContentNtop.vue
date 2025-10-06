<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

import { NtopBase, getIfid } from './ntop.ts'
import type { ContentProps, NtopType } from './types.ts'

const props = defineProps<ContentProps>()

let ntop: NtopBase | undefined = undefined
const interfaceDivId: string = 'ntop_interface_quickstats'
const contentDivId: string = `db-content-ntop-${props.widget_id}`
let ifid: string

onMounted(async () => {
  ifid = await getIfid()
  ntop = new NtopBase(props.content.type as NtopType, interfaceDivId, contentDivId, ifid)
})

onBeforeUnmount(() => {
  if (ntop) {
    ntop.disable()
  }
})
</script>

<template>
  <div
    class="db-content-ntop__wrapper ntop"
    :class="{
      'db-content-ntop__background': !!general_settings.render_background
    }"
  >
    <div :id="interfaceDivId" class="ntop_interface_quickstats" />
    <div :id="contentDivId" class="db-content-ntop" />
  </div>
</template>

<style scoped>
.db-content-ntop__wrapper {
  width: 100%;
  height: 100%;
  padding-top: var(--dimension-2);
}

.db-content-ntop__background {
  background-color: var(--db-content-bg-color);
}
</style>
