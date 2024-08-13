<script setup lang="ts">
import { computed } from 'vue'
import { Collapsible, CollapsibleContent } from '@/components/ui/collapsible'
import { Label } from '@/components/ui/label'

import QuickSetupStageContent from './QuickSetupStageContent.vue'
import CompositeWidget from './widgets/CompositeWidget.vue'
import Button from './element/IconButton.vue'
import LoadingIcon from '@/components/common/LoadingIcon.vue'
import ErrorBoundary from '@/components/common/ErrorBoundary.vue'

import { type QuickSetupStageWithIndexSpec, type StageData } from './quick_setup_types'

const emit = defineEmits(['prevStage', 'nextStage', 'save', 'update'])
const props = defineProps<QuickSetupStageWithIndexSpec>()

const isFirst = computed(() => props.index == 0)
const isCompleted = computed(() => props.index < props.selectedStage)

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
      complete: props.index < props.selectedStage
    }"
  >
    <div class="qs-stage__content">
      <Label variant="title">{{ props.spec.title }}</Label>

      <ErrorBoundary>
        <CompositeWidget v-if="isCompleted" :items="props.spec.recap || []" />
      </ErrorBoundary>

      <Collapsible :open="props.index == props.selectedStage">
        <CollapsibleContent>
          <div style="padding-left: 1rem">
            <div v-if="props.spec.sub_title">
              <Label variant="subtitle">{{ props.spec.sub_title }}</Label>
            </div>
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
              :label="props.spec.next_button_label || 'Next'"
              variant="next"
              @click="$emit('nextStage')"
            />
            <Button
              v-if="!isFirst"
              style="padding-left: 1rem"
              label="Back"
              variant="prev"
              @click="$emit('prevStage')"
            />
          </div>
          <div v-else class="qs-stage__loading"><LoadingIcon :height="16" />Please wait...</div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  </li>
</template>

<style scoped>
.qs-stage {
  position: relative;
  display: flex;
  gap: 1rem;
  padding-bottom: 1rem;

  &:before {
    --size: 3rem;
    counter-increment: stage-index;
    content: counter(stage-index);
    align-content: center;
    text-align: center;
    font-size: large;
    font-weight: bold;
    margin-right: 1rem;
    position: relative;
    z-index: 1;
    flex: 0 0 var(--size);
    height: var(--size);
    border-radius: 50%;
    color: #212121;
    background-color: lightgrey;
  }

  &.active:before,
  &.complete:before {
    background-color: #17b78e;
  }

  &:not(:last-child):after {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    transform: translateX(1.5rem);
    width: 2px;
    background-color: #e0e0e0;
  }

  &.active:not(:last-child):after,
  &.complete:not(:last-child):after {
    background-color: #17b78e;
  }
}

.qs-stage__content {
  padding-top: 1rem;
}

.qs-stage__action {
  padding-top: 1rem;
  position: relative;
  left: -0.8rem;
}

.qs-stage__loading {
  padding-left: 1rem;
}
</style>
