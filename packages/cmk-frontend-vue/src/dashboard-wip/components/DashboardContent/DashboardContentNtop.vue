<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { inject, onBeforeUnmount, onMounted, ref } from 'vue'

import { cmkTokenKey } from '@/dashboard-wip/types/injectionKeys.ts'

import { NtopBase, getIfid } from './ntop.ts'
import type { ContentProps, NtopType } from './types.ts'

const props = defineProps<ContentProps>()
const cmkToken = inject(cmkTokenKey) as string | undefined

let ntop: NtopBase | undefined = undefined
const interfaceDivId: string = 'ntop_interface_quickstats'
const contentDivId: string = `db-content-ntop-${props.widget_id}`
let ifid: string
const errorMessage = ref<string | null>(null)

onMounted(async () => {
  try {
    ifid = await getIfid(cmkToken)
    ntop = new NtopBase(
      props.content.type as NtopType,
      interfaceDivId,
      contentDivId,
      ifid,
      cmkToken
    )
  } catch (error) {
    // Can't let the site crash because of ntop errors, they are for the user
    errorMessage.value = (error as Error).message
  }
})

onBeforeUnmount(() => {
  if (ntop) {
    ntop.disable()
  }
})
</script>

<template>
  <div v-if="errorMessage" class="db-content-ntop__error error">
    {{ errorMessage }}
  </div>
  <div
    v-else
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

.db-content-ntop__error {
  max-width: 95%;
}
</style>
