<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'

import { NtopBase, getIfid } from './ntop.ts'
import type { ContentProps, NtopType } from './types.ts'

const props = defineProps<ContentProps>()
const cmkToken = useInjectCmkToken()

let ntop: NtopBase | undefined = undefined
const interfaceDivId: string = 'ntop_interface_quickstats'
const contentDivId: string = `db-content-ntop-${props.widget_id}`
let ifid: string
const exception = ref<{ class: 'warning' | 'error'; msg: string } | null>(null)

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
  } catch (exc) {
    // Can't let the site crash because of ntop warnings, they are for the user
    // e.g. ntopng integration is not activated under global settings.
    if (exc instanceof Error) {
      exception.value = {
        class: 'error',
        msg: exc.message
      }
    } else {
      exception.value = {
        class: 'warning',
        msg: exc as string
      }
    }
  }
})

onBeforeUnmount(() => {
  if (ntop) {
    ntop.disable()
  }
})
</script>

<template>
  <div v-if="exception" :class="['db-content-ntop__warning', exception.class]">
    {{ exception.msg }}
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

.db-content-ntop__warning {
  max-width: 95%;
}
</style>
