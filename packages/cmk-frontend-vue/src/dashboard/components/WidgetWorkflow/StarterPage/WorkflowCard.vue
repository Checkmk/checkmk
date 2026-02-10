<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkIconEmblem from '@/components/CmkIcon/CmkIconEmblem.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import DisabledTooltipWrapper from '../DisabledTooltipWrapper.vue'
import type { WorkflowItem } from '../WidgetWorkflowTypes'

interface WorkflowCardProps extends WorkflowItem {
  disabled?: boolean
}

const props = defineProps<WorkflowCardProps>()

const emit = defineEmits(['select'])

const doSelect = () => {
  if (!props.disabled) {
    emit('select')
  }
}
</script>

<template>
  <DisabledTooltipWrapper :disabled="!!disabled">
    <a
      href="#"
      class="db-workflow-card"
      :class="{ 'db-workflow-card__disabled': disabled }"
      @click="doSelect"
    >
      <CmkIconEmblem :emblem="icon_emblem"><CmkIcon :name="icon" size="xxlarge" /></CmkIconEmblem>
      <div class="db-workflow-card__content">
        <CmkHeading type="h2">
          {{ title }}
        </CmkHeading>
        <CmkParagraph class="db-workflow-card__subtitle">{{ subtitle }}</CmkParagraph>
      </div>
    </a>
  </DisabledTooltipWrapper>
</template>

<style scoped>
.db-workflow-card {
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

.db-workflow-card__disabled {
  pointer-events: none;
  opacity: 0.5;
}

.db-workflow-card__content {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.db-workflow-card__subtitle {
  min-height: 2em;
  color: var(--font-color-dimmed);
}
</style>
