<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
export const codeExample = `<script setup lang="ts">
${'import'} CmkZebra from '@/components/CmkZebra.vue'

const items = [
  'Demonstration of of row context for index 0',
  'Demonstration of of row context for index 1',
  'Demonstration of of row context for index 2'
]
<${'/'}script>

<template>
  <CmkZebra v-for="(item, index) in items" :key="index" :num="index">
    {{ item }}
  </CmkZebra>
</template>`
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'

import CmkZebra from '@/components/CmkZebra.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkZebra</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-cmk-zebra__container">
        <CmkZebra v-for="index in 5" :key="index" :num="index - 1" class="ucl-cmk-zebra__row">
          Demonstration row content for index {{ index - 1 }}
        </CmkZebra>
      </div>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-cmk-zebra__container {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.ucl-cmk-zebra__row {
  padding: 12px;
  background-color: var(--default-bg-color);
}
</style>
