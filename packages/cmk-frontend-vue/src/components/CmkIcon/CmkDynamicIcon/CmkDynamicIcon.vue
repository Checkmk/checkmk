<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<!--
This icon variant should be used if the icon can be changed by the user and is
saved in the backend. An example for this would be a dashboard: The user can
choose which icon should be used. If you want to render such this icon you
should use CmkDynamicIcon.

If you know at buildtime which icon should be shown, use the classic CmkIcon.
-->
<script setup lang="ts">
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'

import CmkIconEmblem from '@/components/CmkIcon/CmkIconEmblem.vue'

import { type IconEmblems, type IconSizeNames } from '../types'
import CmkDynamicIconUserOrDefault from './CmkDynamicIconUserOrDefault.vue'

interface CmkDynamicIconProps {
  spec: DynamicIcon
  size?: IconSizeNames | undefined
  title?: string | undefined
}

defineOptions({ inheritAttrs: false })

const props = defineProps<CmkDynamicIconProps>()
</script>

<template>
  <CmkIconEmblem v-if="props.spec.type === 'emblem_icon'" :emblem="props.spec.emblem as IconEmblems"
    ><CmkDynamicIconUserOrDefault
      :spec="props.spec.icon"
      :size="props.size"
      v-bind="$attrs"
      :title="props.title"
  /></CmkIconEmblem>
  <CmkDynamicIconUserOrDefault
    v-else
    :spec="props.spec"
    :size="props.size"
    v-bind="$attrs"
    :title="props.title"
  />
</template>
