<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import type { OneColorIcons } from 'cmk-ui-library/components/CmkIcon/types'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

defineProps<{
  iconName: OneColorIcons
  title: string
}>()

defineEmits<{
  click: []
}>()
</script>

<template>
  <button class="db-responsive-grid-widget-button__button" @click.prevent="$emit('click')">
    <span class="db-responsive-grid-widget-button__highlight">
      <CmkMultitoneIcon
        class="db-responsive-grid-widget-button__icon"
        :name="iconName"
        :title="title"
        :aria-label="title as TranslatedString"
        :primary-color="{ custom: 'var(--db-rgw-button-color)' }"
        size="xlarge"
      />
    </span>
  </button>
</template>

<style scoped>
.db-responsive-grid-widget-button__button {
  /* match size of the header height */
  width: var(--dimension-8);
  height: var(--dimension-8);
  margin: 0;
  padding: 0;
  border: none;
  border-radius: 0;
  cursor: pointer;
  background: var(--background-control);
}

.db-responsive-grid-widget-button__icon {
  --db-rgw-button-color: var(--font-color-secondary);
}

.db-responsive-grid-widget-button__highlight {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background-color: var(--background-hover-overlay);

    & > .db-responsive-grid-widget-button__icon {
      --db-rgw-button-color: var(--font-color);
    }
  }
}
</style>
