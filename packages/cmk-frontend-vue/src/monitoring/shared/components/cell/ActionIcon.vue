<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
import type {
  CmkMultitoneIconColor,
  CmkMultitoneIconNames,
  SimpleIcons
} from 'cmk-ui-library/components/CmkIcon/types'

export interface MultitoneActionIcon {
  name: CmkMultitoneIconNames
  color: NonNullable<CmkMultitoneIconColor>
}

// A bare name is a themed bitmap icon, an object is an inline multitone SVG.
export type ActionIcon = SimpleIcons | MultitoneActionIcon
</script>

<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import type { IconSizeNames } from 'cmk-ui-library/components/CmkIcon/types'

withDefaults(defineProps<{ icon: ActionIcon; size?: IconSizeNames }>(), { size: 'small' })
</script>

<template>
  <CmkMultitoneIcon
    v-if="typeof icon !== 'string'"
    :name="icon.name"
    :primary-color="icon.color"
    :size="size"
  />
  <CmkIcon v-else :name="icon" :size="size" />
</template>
