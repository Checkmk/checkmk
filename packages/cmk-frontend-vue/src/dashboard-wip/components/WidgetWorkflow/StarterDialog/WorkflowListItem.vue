<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import IconWithEmblem from '../IconWithEmblem.vue'
import type { WorkflowItem } from '../WidgetWorkflowTypes'

defineProps<WorkflowItem>()
const emit = defineEmits(['select'])
</script>

<template>
  <button class="db-workflow-list-item" @click="emit('select')">
    <IconWithEmblem :icon="icon" :icon_emblem="icon_emblem" />
    <div class="db-workflow-list-item__content">
      <CmkHeading type="h2">
        {{ title }}
      </CmkHeading>
      <CmkParagraph class="db-workflow-list-item__subtitle">{{ subtitle }}</CmkParagraph>
    </div>
  </button>
</template>

<style scoped>
.db-workflow-list-item {
  display: flex;
  align-items: center;
  gap: var(--dimension-7);
  width: 100%;
  padding: var(--dimension-4) var(--dimension-5);
  text-align: left;
  background-color: var(--ux-theme-1);
  border: var(--dimension-1) solid var(--ux-theme-6);
  border-radius: var(--border-radius);
  cursor: pointer;

  &:hover {
    background-color: var(--ux-theme-5);
  }

  &:focus,
  &:focus-visible {
    outline: var(--default-border-color-green) auto var(--dimension-1);
  }
}

.db-workflow-list-item__content {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.db-workflow-list-item__subtitle {
  color: var(--font-color-dimmed);
}
</style>
