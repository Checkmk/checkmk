<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'
import type {
  CmkMultitoneIconColor,
  CmkMultitoneIconNames,
  IconEmblems,
  SimpleIcons
} from 'cmk-ui-library/components/CmkIcon/types'

export interface MultitoneActionIcon {
  name: CmkMultitoneIconNames
  color: NonNullable<CmkMultitoneIconColor>
  emblem?: IconEmblems | undefined
}

// A bare name is a themed bitmap icon, an object is an inline multitone SVG or, for a custom
// action, an icon the user picked.
export type ActionIcon = SimpleIcons | MultitoneActionIcon | DynamicIcon
</script>

<script setup lang="ts">
import CmkDynamicIcon from 'cmk-ui-library/components/CmkIcon/CmkDynamicIcon/CmkDynamicIcon.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkIconEmblem from 'cmk-ui-library/components/CmkIcon/CmkIconEmblem.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import type { IconSizeNames } from 'cmk-ui-library/components/CmkIcon/types'

withDefaults(defineProps<{ icon: ActionIcon; size?: IconSizeNames }>(), { size: 'small' })
</script>

<template>
  <CmkIcon v-if="typeof icon === 'string'" :name="icon" :size="size" />
  <CmkDynamicIcon v-else-if="'type' in icon" :spec="icon" :size="size" />
  <CmkIconEmblem v-else :emblem="icon.emblem">
    <CmkMultitoneIcon :name="icon.name" :primary-color="icon.color" :size="size" />
  </CmkIconEmblem>
</template>
