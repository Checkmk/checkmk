<script setup lang="ts">
import { computed } from 'vue'
import { Collapsible, CollapsibleContent } from '@/quick-setup/ui/collapsible'
import { Label } from '@/quick-setup/ui/label'

import QuickSetupStageContent from './QuickSetupStageContent.vue'
import CompositeWidget from './widgets/CompositeWidget.vue'
import Button from '@/quick-setup/components/IconButton.vue'
import LoadingIcon from '@/quick-setup/components/LoadingIcon.vue'
import ErrorBoundary from '@/quick-setup/components/ErrorBoundary.vue'

import { type QuickSetupStageWithIndexSpec, type StageData } from './quick_setup_types'

const emit = defineEmits(['prevStage', 'nextStage', 'save', 'update'])
const props = defineProps<QuickSetupStageWithIndexSpec>()

const isFirst = computed(() => props.index == 0)
const isCompleted = computed(() => props.index < props.selectedStage)
const isLast = computed(() => props.index == props.numberOfStages - 1)

let userInput: StageData = (props?.spec.user_input as StageData) || {}

const updateData = (id: string, value: object) => {
  userInput[id] = value
  emit('update', props.index, userInput)
}
</script>

<template>
  <li
    class="qs-stage"
    :class="{
      active: props.index == props.selectedStage,
      complete: isCompleted
    }"
  >
    <div class="qs-stage__content">
      <Label variant="title">{{ props.spec.title }}</Label>
      <Label v-if="!isCompleted && props.spec.sub_title" variant="subtitle">{{
        props.spec.sub_title
      }}</Label>

      <ErrorBoundary>
        <CompositeWidget v-if="isCompleted" :items="props.spec.recap || []" />
      </ErrorBoundary>

      <Collapsible :open="props.index == props.selectedStage">
        <CollapsibleContent>
          <div>
            <QuickSetupStageContent
              :components="props.spec?.components || []"
              :form_spec_errors="props.spec?.form_spec_errors || {}"
              :stage_errors="props.spec?.stage_errors || []"
              :other_errors="props.other_errors || []"
              :user_input="userInput"
              @update="updateData"
            />
          </div>

          <div v-if="!loading" class="qs-stage__action">
            <Button
              v-if="!isLast"
              :label="props.spec.next_button_label || 'Next'"
              variant="next"
              @click="$emit('nextStage')"
            />
            <Button
              v-if="isLast"
              :label="props.spec.next_button_label || 'Save'"
              variant="save"
              @click="$emit('nextStage')"
            />
            <Button v-if="!isFirst" label="Back" variant="prev" @click="$emit('prevStage')" />
          </div>
          <div v-else class="qs-stage__loading">
            <LoadingIcon size="lg" />
            <!-- TODO: move these texts to the backend to make them translatable (CMK-19020) -->
            <span v-if="isLast">This process may take several minutes, please wait...</span>
            <span v-else>Please wait...</span>
          </div>
        </CollapsibleContent>
      </Collapsible>
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
    background-color: lightgrey;
  }

  &.active:before,
  &.complete:before {
    background-color: var(--success-dimmed);
  }

  &.complete:before {
    background-image: var(--icon-check);
    background-repeat: no-repeat;
    background-position: center;
    content: '';
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

  &.active:after {
    background: linear-gradient(
      to bottom,
      var(--success-dimmed) 50px,
      var(--qs-stage-line-color) 50px
    );
  }

  &.complete:after {
    background-color: var(--success-dimmed);
  }
}

.qs-stage__action {
  padding-top: var(--spacing);
  position: relative;
}

.qs-stage__loading {
  display: flex;
  align-items: center;
  padding-top: 12px;
}
</style>
