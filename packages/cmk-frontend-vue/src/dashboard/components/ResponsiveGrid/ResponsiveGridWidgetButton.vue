<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import type { OneColorIcons } from '@/components/CmkIcon/types'

defineProps<{
  iconName: OneColorIcons
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
        :primary-color="{ custom: 'var(--db-rgw-button-color)' }"
        size="xlarge"
      />
    </span>
  </button>
</template>

<style scoped>
.db-responsive-grid-widget-button__button {
  /* match size of the header height */
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 0;
  border: none;
  border-radius: 0;
  cursor: pointer;
  background: var(--color-daylight-grey-60);
}

body[data-theme='modern-dark'] .db-responsive-grid-widget-button__button {
  background: var(--color-midnight-grey-60);
}

.db-responsive-grid-widget-button__icon {
  --db-rgw-button-normal-color: var(--color-conference-grey-70);
  --db-rgw-button-hover-color: var(--color-conference-grey-100);
  --db-rgw-button-color: var(--db-rgw-button-normal-color);
}

body[data-theme='modern-dark'] .db-responsive-grid-widget-button__icon {
  --db-rgw-button-normal-color: var(--color-white-70);
  --db-rgw-button-hover-color: var(--color-white-100);
}

.db-responsive-grid-widget-button__highlight {
  width: 100%;
  height: 100%;

  --db-rgw-button-bg-hover-color: var(--color-white-50);

  &:hover {
    background-color: var(--db-rgw-button-bg-hover-color);

    & > .db-responsive-grid-widget-button__icon {
      --db-rgw-button-color: var(--db-rgw-button-hover-color);
    }
  }
}

body[data-theme='modern-dark'] .db-responsive-grid-widget-button__highlight {
  --db-rgw-button-bg-hover-color: var(--color-white-10);
}
</style>
