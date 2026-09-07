<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkCode from 'cmk-ui-library/components/CmkCode.vue'

import type { RenderedBlock } from '../lib/commandTemplate'

defineProps<{ blocks: RenderedBlock[] }>()
</script>

<template>
  <template v-for="block in blocks" :key="block.text">
    <CmkAlertBox v-if="block.warning" variant="warning">{{ block.warning }}</CmkAlertBox>
    <CmkCode
      v-bind="block.title === undefined ? {} : { title: block.title }"
      :code-text="block.text"
      class="code"
      width="fill"
    />
  </template>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.code {
  margin: var(--dimension-5) 0 var(--dimension-7);
  width: 100%;
}
</style>
