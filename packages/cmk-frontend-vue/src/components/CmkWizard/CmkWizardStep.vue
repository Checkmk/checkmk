<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { getWizardContext } from '@/components/CmkWizard/utils.ts'

export interface CmkWizardStepProps {
  index: number
  isCompleted: () => boolean
}
const context = getWizardContext()

const props = defineProps<CmkWizardStepProps>()

function onClickGoTo() {
  context.navigation.goto(props.index)
}
</script>

<template>
  <li
    class="cmk-wizard-step-row"
    :class="{
      'wizard-step--active': context.isSelected(index) && context.mode() !== 'overview',
      'wizard-step--complete': isCompleted() && context.mode() !== 'overview'
    }"
    @click="(_mouse_event) => onClickGoTo"
  >
    <div class="cmk-wizard-step__slots">
      <slot name="header"></slot>
      <slot name="content"></slot>
      <div v-if="context.isSelected(index)" class="cmk-wizard-step__actions">
        <slot name="actions"></slot>
      </div>
    </div>
  </li>
</template>

<style scoped>
.cmk-wizard-step-row {
  position: relative;
  display: flex;
  gap: var(--dimension-6);

  --wizard-step-number-badge-width: var(--dimension-8);
  --wizard-progress-bar-width: var(--dimension-2);

  &:not(:last-child) {
    padding-bottom: 1rem;
  }

  /* Step number badge */
  &::before {
    counter-increment: stage-index;
    content: counter(stage-index);
    align-content: center;
    text-align: center;
    font-size: var(--font-size-normal);
    font-weight: bold;
    position: relative;
    z-index: 1;
    flex: 0 0 var(--wizard-step-number-badge-width);
    height: var(--wizard-step-number-badge-width);
    border-radius: 50%;
    color: var(--wizard-progress-bar-background-color);
    border: var(--wizard-progress-bar-width) solid var(--wizard-progress-bar-background-color);
    background-color: transparent;
    box-sizing: border-box;
  }

  /* Connecting line between badges */
  &:not(:last-child)::after {
    content: '';
    position: absolute;
    left: calc(var(--wizard-step-number-badge-width) / 2 - 1px);
    top: var(--wizard-step-number-badge-width);
    bottom: 0;
    width: var(--wizard-progress-bar-width);
    background-color: var(--wizard-progress-bar-background-color);
  }

  &.wizard-step--active::before,
  &.wizard-step--complete::before {
    background-color: var(--success-dimmed);
    border-color: var(--success-dimmed);
  }

  &.wizard-step--active::after {
    background: linear-gradient(
      to bottom,
      var(--success-dimmed) 50px,
      var(--wizard-progress-bar-background-color) 50px
    );
  }

  &.wizard-step--complete {
    &::before {
      background-image: var(--icon-check);
      background-repeat: no-repeat;
      background-position: center;
      content: '';
    }

    &::after {
      background-color: var(--success-dimmed);
    }
  }
}

.cmk-wizard-step__slots {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.cmk-wizard-step__actions {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-4);
}
</style>
