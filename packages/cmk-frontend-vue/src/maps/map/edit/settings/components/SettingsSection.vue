<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A block of settings that only one kind of map has, under its own heading.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

defineProps<{ title: TranslatedString }>()
</script>

<template>
  <section class="maps-settings-section">
    <CmkHeading type="h4" class="maps-settings-section__title">{{ title }}</CmkHeading>
    <div class="maps-settings-section__fields"><slot /></div>
  </section>
</template>

<style scoped>
.maps-settings-section {
  padding-top: var(--dimension-5);
  border-top: 1px solid var(--default-border-color);
}

.maps-settings-section__title {
  margin-bottom: var(--dimension-4);
  color: var(--font-color-dimmed);
}

.maps-settings-section__fields {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
}
</style>
