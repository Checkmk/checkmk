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
  <a href="#" class="workflow-card" @click="emit('select')">
    <IconWithEmblem :icon="icon" :icon_emblem="icon_emblem" />
    <div class="workflow-card__content">
      <CmkHeading type="h2">
        {{ title }}
      </CmkHeading>
      <CmkParagraph class="workflow-card__subtitle">{{ subtitle }}</CmkParagraph>
    </div>
  </a>
</template>

<style scoped>
.workflow-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing);
  text-align: center;
  text-decoration: none;
  background-color: var(--ux-theme-1);
  border: var(--dimension-1) solid var(--ux-theme-6);
  border-radius: var(--border-radius);
  padding: var(--dimension-7);
  cursor: pointer;

  &:hover {
    background-color: var(--input-hover-bg-color);
  }

  &:focus,
  &:focus-visible {
    outline: var(--default-border-color-green) auto var(--dimension-1);
  }
}

.workflow-card__content {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.workflow-card__subtitle {
  min-height: 2em;
  color: var(--font-color-dimmed);
}
</style>
