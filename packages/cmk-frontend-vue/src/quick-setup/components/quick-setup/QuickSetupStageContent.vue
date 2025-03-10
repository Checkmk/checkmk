<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkButton from '@/components/CmkButton.vue'
import type { QuickSetupStageContent } from './quick_setup_types'
import QuickSetupStageContentError from './QuickSetupStageContentError.vue'

const props = defineProps<QuickSetupStageContent>()

const loadWaitLabel = ref('')

const isSaveOverview = computed(
  () => props.index === props.numberOfStages && props.mode === 'overview'
)
const showButtons = computed(() => props.mode === 'guided' || isSaveOverview.value)

const filteredActions = computed(() => {
  if (!props.actions) {
    return []
  }
  return props.actions.filter((b) => !isSaveOverview.value || b.variant === 'save')
})

function getButtonConfig(
  variant: 'next' | 'prev' | 'save' | unknown,
  iconName: string = '',
  iconRotate: number = 0
): {
  icon: { name: string; rotate: number }
} {
  if (iconName) {
    return { icon: { name: iconName, rotate: iconRotate } }
  }

  switch (variant) {
    case 'prev':
      return { icon: { name: 'back', rotate: 90 } }

    case 'next':
      return {
        icon: { name: 'continue', rotate: 90 }
      }
    case 'save':
      return {
        icon: { name: 'save-to-services', rotate: 0 }
      }
  }
  return { icon: { name: '', rotate: 0 } }
}

const invokeAction = (waitLabel: string, action: () => void) => {
  loadWaitLabel.value = waitLabel
  action()
}

const waitIconEnabled = computed(() => {
  return typeof props.hideWaitIcon === 'undefined' || !props.hideWaitIcon
})
</script>

<template>
  <div>
    <component :is="content" v-if="content" />

    <QuickSetupStageContentError :errors="errors" />

    <div v-if="showButtons">
      <div v-if="!loading" class="qs-stage-content__action">
        <CmkButton
          v-for="{ action, buttonConfig } in filteredActions.map((act) => {
            return {
              action: act,
              buttonConfig: getButtonConfig(act.variant, act.icon.name, act.icon.rotate)
            }
          })"
          :key="action.label"
          :aria-label="action.ariaLabel"
          :variant="
            action.variant === 'next' || action.variant === 'save' ? 'primary' : 'secondary'
          "
          @click="invokeAction(action.waitLabel, action.action)"
        >
          <CmkIcon
            :name="buttonConfig.icon.name"
            :rotate="buttonConfig.icon.rotate"
            variant="inline"
          />{{ action.label }}
        </CmkButton>
      </div>
      <div v-else-if="waitIconEnabled" class="qs-stage-content__loading">
        <CmkIcon name="load-graph" variant="inline" size="xlarge" />
        <span>{{ loadWaitLabel }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.qs-stage-content__action {
  padding-top: var(--spacing);
  position: relative;
}

.qs-stage-content__action > button {
  margin-right: 8px;
}

.qs-stage-content__loading {
  display: flex;
  align-items: center;
  box-sizing: border-box;
  height: 40px;
  padding-top: 12px;
}
</style>
