<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import CmkCollapsible from '@/components/CmkCollapsible.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import { useErrorBoundary } from '@/components/useErrorBoundary'

import QuickSetupStageContent from './QuickSetupStageContent.vue'
import type { QuickSetupStageProps } from './quick_setup_types'

const props = defineProps<QuickSetupStageProps>()

const isSelectedStage = computed(() => props.index === props.currentStage)
const isCompleted = computed(() => props.index < props.currentStage)
const isOpen = computed(() => isSelectedStage.value || props.mode === 'overview')
const onClickGoTo = computed(() =>
  !!props.goToThisStage && props.currentStage > props.index ? () => props.goToThisStage!() : null
)
// eslint-disable-next-line @typescript-eslint/naming-convention
const { ErrorBoundary } = useErrorBoundary()
</script>

<template>
  <li
    class="qs-stage"
    :class="{
      'qs-stage--active': isSelectedStage && props.mode !== 'overview',
      'qs-stage--complete': isCompleted && props.mode !== 'overview'
    }"
    @click="(_mouse_event) => onClickGoTo"
  >
    <div class="qs-stage__content">
      <CmkLabel variant="title" :on-click="onClickGoTo">{{ title }}</CmkLabel>

      <CmkCollapsible :open="isCompleted && !!recapContent">
        <ErrorBoundary>
          <component :is="recapContent" />
        </ErrorBoundary>
      </CmkCollapsible>

      <CmkCollapsible :open="!isCompleted && !!sub_title">
        <CmkLabel variant="subtitle">{{ sub_title }}</CmkLabel>
      </CmkCollapsible>

      <CmkCollapsible :open="isOpen">
        <QuickSetupStageContent
          :index="index"
          :number-of-stages="numberOfStages"
          :loading="loading"
          :mode="mode"
          :errors="errors"
          :actions="actions"
          :content="content || null"
          :hide-wait-legend="!!hideWaitLegend"
        />
      </CmkCollapsible>
    </div>
  </li>
</template>

<style scoped>
.qs-stage {
  position: relative;
  display: flex;
  gap: 16px;
  padding-bottom: 1rem;

  &:before {
    counter-increment: stage-index;
    content: counter(stage-index);
    align-content: center;
    text-align: center;
    font-size: var(--font-size-normal);
    font-weight: bold;
    position: relative;
    z-index: 1;
    flex: 0 0 24px;
    height: 24px;
    border-radius: 50%;
    color: #212121;
    background-color: var(--qs-stage-line-color);
  }

  &:not(:last-child):after {
    content: '';
    position: absolute;
    left: -1px;
    top: 0;
    bottom: 0;
    transform: translateX(11px);
    width: 3px;
    background-color: var(--qs-stage-line-color);
  }

  &.qs-stage--active:before,
  &.qs-stage--complete:before {
    background-color: var(--success-dimmed);
  }

  &.qs-stage--active:after {
    background: linear-gradient(
      to bottom,
      var(--success-dimmed) 50px,
      var(--qs-stage-line-color) 50px
    );
  }

  &.qs-stage--complete {
    pointer-events: none;

    &:before {
      background-image: var(--icon-check);
      background-repeat: no-repeat;
      background-position: center;
      content: '';
      cursor: pointer;
      pointer-events: all;
    }

    &:after {
      background-color: var(--success-dimmed);
    }
  }
}

.qs-stage__loading {
  display: flex;
  align-items: center;
  padding-top: 12px;
}
</style>
