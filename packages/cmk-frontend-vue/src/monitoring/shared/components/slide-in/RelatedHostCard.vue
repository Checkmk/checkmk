<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

defineProps<{
  title: TranslatedString
  subtitle: TranslatedString
}>()
</script>

<template>
  <div class="monitoring-related-host-card">
    <slot name="leading" />
    <div class="monitoring-related-host-card__text-area">
      <CmkHeading type="h4"
        ><slot name="title">{{ title }}</slot></CmkHeading
      >
      <CmkParagraph class="monitoring-related-host-card__subtitle">{{ subtitle }}</CmkParagraph>
      <div v-if="$slots.default" class="monitoring-related-host-card__content">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.monitoring-related-host-card {
  display: flex;
  align-items: center;
  border: var(--dimension-1) solid transparent;
  border-radius: var(--border-radius);
  background-color: var(--ux-theme-3);
  padding: var(--dimension-4) var(--dimension-5);
}

.monitoring-related-host-card__text-area {
  flex: 1 1 auto;
  min-width: 0;
  overflow-wrap: anywhere;
}

.monitoring-related-host-card__subtitle {
  color: var(--font-color-secondary);
}

.monitoring-related-host-card__content {
  margin-top: var(--dimension-4);
}
</style>
