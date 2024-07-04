<script setup lang="ts">
import { computed } from 'vue'
import { Collapsible, CollapsibleContent } from '@/components/ui/collapsible'
import { Label } from '@/components/ui/label'

import CompositeWidget from '@/components/quick-setup/widgets/CompositeWidget.vue'
import Button from '@/components/IconButton.vue'
import LoadingIcon from '@/components/LoadingIcon.vue'
import StepNumber from './element/StepNumber.vue'
import ErrorBoundary from '@/components/ErrorBoundary.vue'

import { type QuickSetupStepWithIndexSpec, type StageData } from './quick_setup_types'
import AlertBox from '../AlertBox.vue'

const emit = defineEmits(['prevStep', 'nextStep', 'save', 'update'])
const props = defineProps<QuickSetupStepWithIndexSpec>()

const isFirst = computed(() => props.index == 0)
const isLast = computed(() => props.index == props.steps - 1)
const isCompleted = computed(() => props.index < props.selectedStep)

let userInput: StageData = (props?.spec.user_input as StageData) || {}

const updateData = (id: string, value: object) => {
  userInput[id] = value
  emit('update', props.index, userInput)
}
</script>

<template>
  <li
    class="cmk-stepper__item"
    :class="{
      active: props.index == props.selectedStep,
      complete: props.index < props.selectedStep
    }"
  >
    <div class="cmk-stepper__content">
      <StepNumber
        :number="index + 1"
        :active="props.index == props.selectedStep"
        :complete="props.index < props.selectedStep"
      />
      <Label class="cmk-stepper__title">{{ props.spec.title }}</Label>

      <ErrorBoundary>
        <CompositeWidget v-if="isCompleted" :items="props.spec.recap || []" @update="updateData" />
      </ErrorBoundary>

      <Collapsible :open="props.index == props.selectedStep" class="cmk-stepper__content">
        <CollapsibleContent class="cmk-animated-collapsible">
          <div style="padding-left: 1rem">
            <div v-if="props.spec.sub_title">
              <Label class="cmk-stepper__subtitle">{{ props.spec.sub_title }}</Label>
            </div>
            <AlertBox v-if="props.spec?.other_errors?.length" variant="error">
              <ul>
                <li v-for="error in props.spec.other_errors" :key="error">{{ error }}</li>
              </ul>
            </AlertBox>
            <ErrorBoundary>
              <CompositeWidget
                v-if="props.spec?.components"
                :items="props.spec.components"
                :data="userInput"
                :errors="props.spec?.form_spec_errors || {}"
                @update="updateData"
              />
            </ErrorBoundary>
          </div>

          <div v-if="!loading" class="cmk-stepper__action">
            <Button
              v-if="!isLast"
              :label="props.spec.next_button_label || 'Next'"
              variant="next"
              @click="$emit('nextStep')"
            />
            <Button v-if="isLast" label="Save" variant="save" @click="$emit('save')" />
            <Button
              v-if="!isFirst"
              style="padding-left: 1rem"
              label="Back"
              variant="prev"
              @click="$emit('prevStep')"
            />
          </div>
          <div v-else class="cmk-stepper__loading"><LoadingIcon :height="16" /> Please wait...</div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  </li>
</template>

<style scoped>
.cmk-stepper__loading {
  padding-left: 1rem;
}
.cmk-stepper__item {
  position: relative;
  display: flex;
  gap: 1rem;
  padding-bottom: 1rem;
}

.cmk-stepper__item:not(:last-child):after {
  top: calc(var(--size) + var(--spacing));
  transform: translateX(calc(var(--size) / 2));
  bottom: var(--spacing);
}

.cmk-stepper__item.active:before,
.cmk-stepper__item.complete:before {
  background-color: #17b78e;
}

.cmk-stepper__item:before {
  --size: 3rem;
  content: '';
  position: relative;
  z-index: 1;
  flex: 0 0 var(--size);
  height: var(--size);
  border-radius: 50%;
  background-color: lightgrey;
}

.cmk-stepper__item:not(:last-child):after {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  transform: translateX(1.5rem);
  width: 2px;
  background-color: #e0e0e0;
}

.cmk-stepper__item.active:not(:last-child):after,
.cmk-stepper__item.complete:not(:last-child):after {
  background-color: #17b78e;
}

.cmk-stepper__title {
  font-weight: bold;
  font-size: large;
  position: relative;
  top: -0.2rem;
}

.cmk-stepper__subtitle {
  font-weight: normal;
  font-size: small;
  position: relative;
}

.cmk-stepper__content {
  padding-top: 1rem;
}

.cmk-stepper__action {
  padding-top: 1rem;
  position: relative;
  left: -1rem;
}

.cmk-animated-collapsible {
  overflow: hidden;
}

.cmk-animated-collapsible[data-state='open'] {
  animation: slideDown 300ms ease-out;
}
.cmk-animated-collapsible[data-state='closed'] {
  animation: slideUp 300ms ease-out;
}

@keyframes slideDown {
  from {
    height: 0;
  }
  to {
    height: var(--radix-collapsible-content-height);
  }
}

@keyframes slideUp {
  from {
    height: var(--radix-collapsible-content-height);
  }
  to {
    height: 0;
  }
}
</style>
