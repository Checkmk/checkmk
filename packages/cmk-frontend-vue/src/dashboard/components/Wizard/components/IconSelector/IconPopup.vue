<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'
import { computed, nextTick, onBeforeUnmount, onMounted, onUnmounted, ref } from 'vue'

import usei18n from '@/lib/i18n'
import useClickOutside from '@/lib/useClickOutside'

import CmkButton from '@/components/CmkButton.vue'
import CmkToggleButtonGroup from '@/components/CmkToggleButtonGroup.vue'

import IconGallery from './IconGallery.vue'
import type { IconCategory } from './types'

const { _t } = usei18n()

interface IconPopupProps {
  categories: IconCategory[]
  icons: DynamicIcon[]
}

interface IconPopupEmit {
  selectIcon: [DynamicIcon | null]
  close: []
}

const props = defineProps<IconPopupProps>()
const emit = defineEmits<IconPopupEmit>()
const category = defineModel<string | null>('category', { required: true, default: null })
const ready = ref<boolean>(false)
const displayNames = ref<boolean>(false)

const popup = ref<HTMLElement | null>(null)
const left = ref<number | null>(null)

const moveInsideScreen = () => {
  const el = popup.value
  if (!el) {
    return
  }

  const rect = el.getBoundingClientRect()

  if (left.value === null) {
    left.value = rect.left
  }

  if (rect.right > window.innerWidth) {
    left.value = Math.max(0, left.value - (rect.right - window.innerWidth))
  }
}

const style = computed(() => ({
  left: left.value !== null ? `${left.value}px` : undefined
}))

const options = computed(() => {
  return props.categories.map((category) => {
    return {
      label: category.alias,
      value: category.id,
      disabled: false
    }
  })
})

const handleUpdateCategory = (newValue: string | null) => {
  category.value = newValue
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    emit('close')
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown)

  await nextTick()
  moveInsideScreen()
  window.addEventListener('resize', moveInsideScreen)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', moveInsideScreen)
})

const vClickOutside = useClickOutside()
const handleClickOutside = () => {
  if (!ready.value) {
    ready.value = true
    return
  }
  emit('close')
}
</script>

<template>
  <div ref="popup" v-click-outside="handleClickOutside" class="db-icon-popup__popup" :style="style">
    <div v-if="categories.length > 1" class="db-icon-popup__popup-header">
      <CmkToggleButtonGroup
        :model-value="category!"
        :options="options"
        @update:model-value="handleUpdateCategory"
      />
    </div>

    <div class="db-icon-popup__popup-body">
      <IconGallery
        :icons="icons"
        :display-names="displayNames"
        @select-icon="(i) => emit('selectIcon', i)"
      />
    </div>

    <div class="db-icon-popup__popup-footer">
      <div class="db-icon-popup__popup-footer-buttons">
        <CmkButton
          class="db-icon-popup__button"
          variant="optional"
          @click="displayNames = !displayNames"
          >{{ _t('Toggle names') }}</CmkButton
        >

        <CmkButton
          class="db-icon-popup__button"
          variant="optional"
          @click="emit('selectIcon', null)"
          >{{ _t('Select none') }}</CmkButton
        >
      </div>
    </div>
  </div>
</template>
<style scoped>
.db-icon-popup__popup {
  position: fixed;
  z-index: var(--z-index-popup-offset);
  width: 500px;
  height: 240px;
  color: var(--font-color);
  background-color: var(--ux-theme-0);
  border: var(--dimension-1) solid var(--ux-theme-8);
  border-radius: var(--dimension-3);
  box-shadow: 0 2px 10px rgb(0 0 0 / 20%);
  resize: both;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.db-icon-popup__popup-header {
  flex: 0 0 auto;
  padding: var(--dimension-3);
}

.db-icon-popup__popup-footer {
  justify-items: flex-end;
  border-top: var(--dimension-1) solid var(--ux-theme-8);
  padding: var(--dimension-3);
  flex: 0 0 auto;
}

.db-icon-popup__popup-body {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
}

.db-icon-popup__popup-footer-buttons {
  display: flex;
  flex-direction: row;
  justify-content: flex-end;
  gap: var(--spacing);
}

.db-icon-popup__button {
  height: var(--form-field-height);
}
</style>
