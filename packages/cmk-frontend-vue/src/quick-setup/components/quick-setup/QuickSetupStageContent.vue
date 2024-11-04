<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkButton from '@/components/CmkButton.vue'
import AlertBox from '@/components/AlertBox.vue'
import type { QuickSetupStageContent } from './quick_setup_types'

const props = defineProps<QuickSetupStageContent>()

const isSaveOverview = computed(
  () => props.index === props.numberOfStages && props.mode === 'overview'
)
const showButtons = computed(() => props.mode === 'guided' || isSaveOverview.value)
const filteredButtons = computed(() =>
  props.buttons.filter((b) => !isSaveOverview.value || b.variant === 'save')
)

function getButtonConfig(variant: 'next' | 'prev' | 'save' | unknown): {
  icon: { name: string; rotate: number }
} {
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
</script>

<template>
  <div>
    <component :is="content" v-if="content" />

    <AlertBox v-if="errors && errors.length > 0" variant="error">
      <p v-for="error in errors" :key="error">{{ error }}</p>
    </AlertBox>

    <div v-if="showButtons">
      <div v-if="!loading" class="qs-stage-content__action">
        <CmkButton
          v-for="{ button, buttonConfig } in filteredButtons.map((btn) => {
            return { button: btn, buttonConfig: getButtonConfig(btn.variant) }
          })"
          :key="button.label"
          :aria-label="button.ariaLabel"
          :variant="
            button.variant === 'next' || button.variant === 'save' ? 'primary' : 'secondary'
          "
          @click="button.action"
        >
          <CmkIcon
            :name="buttonConfig.icon.name"
            :rotate="buttonConfig.icon.rotate"
            variant="inline"
          />{{ button.label }}
        </CmkButton>
      </div>
      <div v-else class="qs-stage-content__loading">
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

.qs-stage-content__loading {
  display: flex;
  align-items: center;
  padding-top: 12px;
}
</style>
