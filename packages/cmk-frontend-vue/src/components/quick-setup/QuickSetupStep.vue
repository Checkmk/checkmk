<script setup lang="ts">
import { Collapsible, CollapsibleContent } from '@/components/ui/collapsible'
import { Label } from '@/components/ui/label'
import StepNumber from './element/StepNumber.vue'

import { type OverviewSpec, type StageSpec, type StepData } from '@/quick_setup_types'

import CompositeWidget from '@/components/quick-setup/widgets/CompositeWidget.vue'

import Button from '@/components/IconButton.vue'

interface QuickSetupStepWithIndexSpec {
  /**@property {number} index - The index of the current step */
  index: number

  /**@property {number} steps - Total steps count */
  steps: number

  /**@property {number} selectedStep - The selected step's index  */
  selectedStep: number

  /**@property {StepData} data - User's data input */
  data?: StepData

  /** @property {OverviewSpec} overview - Overview information (title, subtitle, etc) */
  overview: OverviewSpec

  /** @property {StageSpec} stage - Components to be rendered when the step is selected */
  stage?: StageSpec | null

  /**@property {string} nextTitle - Title of the next step. It can be used as "next" button label  */
  nextTitle?: string //Used as label of next button

  /**@property {string} prevTitle - Title of the previous step. It can be used as "previous" button label  */
  prevTitle?: string //Used as label of back button
}

const emit = defineEmits(['prevStep', 'nextStep', 'save', 'update'])
const props = defineProps<QuickSetupStepWithIndexSpec>()

const isFirst = props.index == 0
const isLast = props.index == props.steps - 1

//Here we will store the user input. The key is the form's id.
let userInput: StepData = props?.data || {}

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
      <Label class="cmk-stepper__title">{{ props.overview.title }}</Label>
      <Collapsible :open="props.index == props.selectedStep" class="cmk-stepper__content">
        <CollapsibleContent class="cmk-animated-collapsible">
          <div style="padding-left: 1rem">
            <div v-if="props.overview.sub_title">
              <Label class="cmk-stepper__subtitle">{{ props.overview.sub_title }}</Label>
            </div>

            <CompositeWidget
              v-if="props.stage"
              :components="props.stage.components"
              @update="updateData"
            />
          </div>

          <div class="cmk-stepper__action">
            <Button
              v-if="!isFirst"
              style="padding-left: 1rem"
              :label="props.prevTitle || 'Back'"
              variant="prev"
              @click="$emit('prevStep')"
            />
            <Button
              v-if="!isLast"
              :label="props.nextTitle || 'Next'"
              variant="next"
              @click="$emit('nextStep')"
            />
            <Button v-if="isLast" label="Save" variant="save" @click="$emit('save')" />
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  </li>
</template>

<style scoped>
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
