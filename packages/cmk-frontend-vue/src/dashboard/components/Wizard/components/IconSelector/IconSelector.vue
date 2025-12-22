<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { watch } from 'vue'

import IconSelectorDropdown from './IconSelectorDropdown.vue'
import { useIcons } from './composables/useIcons'
import { getIconId } from './utils'

interface IconSelectorProps {
  selectEmblems?: boolean
}

const props = defineProps<IconSelectorProps>()

const selectedIcon = defineModel<string | null>('selectedIcon', {
  required: false,
  default: null
})

const iconType = props.selectEmblems ? 'emblem' : 'icon'
const handler = await useIcons(iconType, selectedIcon.value)

watch(
  [handler.icon],
  ([newIcon]) => {
    if (!newIcon) {
      selectedIcon.value = null
      return
    }
    selectedIcon.value = getIconId(newIcon)
  },
  { deep: true }
)
</script>

<template>
  <IconSelectorDropdown
    v-model:category="handler.category.value"
    v-model:icon="handler.icon.value"
    :categories="handler.categories.value"
    :icons="handler.icons.value"
  />
</template>
