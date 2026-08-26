<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAccordion from 'cmk-ui-library/components/CmkAccordion/CmkAccordion.vue'
import CmkAccordionItem from 'cmk-ui-library/components/CmkAccordion/CmkAccordionItem.vue'
import { ref } from 'vue'

const openedItems = ref<string[]>([])
</script>

<template>
  <div class="ucl-detail-page-developer-playground__section">
    <CmkAccordion v-model="openedItems" :max-open="1" :min-open="0">
      <CmkAccordionItem value="developer-playground">
        <template #header>
          <span> Developer Playground </span>
        </template>

        <template #content>
          <slot></slot>
        </template>
      </CmkAccordionItem>
    </CmkAccordion>
  </div>
</template>

<style scoped>
.ucl-detail-page-developer-playground__section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
}
</style>
