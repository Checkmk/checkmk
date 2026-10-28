<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'

defineProps<{
  title: string
  description: string
  sections: string[]
}>()
</script>

<template>
  <div class="monitoring-host-slide-in-placeholder">
    <CmkHeading type="h3">{{ title }}</CmkHeading>
    <CmkParagraph class="monitoring-host-slide-in-placeholder__description">
      {{ description }}
    </CmkParagraph>
    <ul class="monitoring-host-slide-in-placeholder__sections">
      <li v-for="section in sections" :key="section">{{ section }}</li>
    </ul>
  </div>
</template>

<style scoped>
.monitoring-host-slide-in-placeholder {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.monitoring-host-slide-in-placeholder__description {
  color: var(--font-color-dimmed);
}

.monitoring-host-slide-in-placeholder__sections {
  margin: 0;
  padding-left: var(--spacing);
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}
</style>
