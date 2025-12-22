<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDynamicIcon from '@/components/CmkIcon/CmkDynamicIcon/CmkDynamicIcon.vue'

import IconPopup from './IconPopup.vue'
import type { IconCategory } from './types'
import { getIconId } from './utils'

const { _t } = usei18n()

interface IconSelectorDropdownProps {
  categories: IconCategory[]
  icons: DynamicIcon[]
}

defineProps<IconSelectorDropdownProps>()
const category = defineModel<string | null>('category', { required: true, default: null })
const icon = defineModel<DynamicIcon | null>('icon', { required: false, default: null })

const displayGallery = ref<boolean>(false)
const displayIcon = computed((): DynamicIcon => {
  return icon.value
    ? icon.value
    : {
        type: 'default_icon',
        id: 'empty'
      }
})

const handleSelectIcon = (selectedIcon: DynamicIcon | null) => {
  displayGallery.value = false
  icon.value = selectedIcon
}

const iconTitle = computed((): string => {
  return icon.value ? getIconId(icon.value)! : _t('No icon selected')
})
</script>

<template>
  <div
    class="db-icon-selector-dropdown__preview"
    :title="iconTitle"
    @click="displayGallery = !displayGallery"
  >
    <CmkDynamicIcon :spec="displayIcon" size="xlarge" />
  </div>
  <div v-if="displayGallery" class="db-icon-selector-dropdown__selector">
    <IconPopup
      v-model:category="category"
      :categories="categories"
      :icons="icons"
      @select-icon="handleSelectIcon"
      @close="displayGallery = false"
    />
  </div>
</template>

<style scoped>
.db-icon-selector-dropdown__preview {
  cursor: pointer;
}
</style>
