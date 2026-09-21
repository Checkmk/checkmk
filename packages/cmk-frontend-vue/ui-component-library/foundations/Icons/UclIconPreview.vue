<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
// Fixed demo colors for the multitone previews. The color prop takes semantic
// keys (mapped to palette colors inside the component), not raw color names.
export const MULTITONE_PRIMARY = 'success'
export const MULTITONE_SECONDARY = 'info'

export type IconKind = 'CmkIcon' | 'CmkMultitoneIcon'
export type IconType = 'svg' | 'png'

export type IconEntry = {
  name: string
  kind: IconKind
  type: IconType
  themed: boolean
  twoColor: boolean
  // Stable v-for key, baked in so the template does not recompute it per render.
  key: string
  // Lowercased name plus curated synonym keywords, baked in once so filtering is
  // a single substring test instead of re-deriving the keyword list per keystroke.
  search: string
}
</script>

<script setup lang="ts">
import type { CmkMultitoneIconNames, IconSizeNames } from 'cmk-ui-library/components/CmkIcon'
import CmkIcon, { type SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'

defineProps<{ icon: IconEntry; size: IconSizeNames }>()
</script>

<template>
  <CmkIcon v-if="icon.kind === 'CmkIcon'" :name="icon.name as SimpleIcons" :size="size" />
  <CmkMultitoneIcon
    v-else
    :name="icon.name as CmkMultitoneIconNames"
    :primary-color="MULTITONE_PRIMARY"
    :secondary-color="icon.twoColor ? MULTITONE_SECONDARY : undefined"
    :size="size"
  />
</template>
