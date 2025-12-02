<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { DefaultIcon, UserIcon } from 'cmk-shared-typing/typescript/icon'
import { computed } from 'vue'

import { untranslated } from '@/lib/i18n'

import CmkIcon, { type IconSizeNames, type SimpleIcons } from '@/components/CmkIcon'

import { iconSizeNametoNumber } from '../utils'

const iconSize = computed(() => iconSizeNametoNumber(props.size))

const props = defineProps<{
  spec: DefaultIcon | UserIcon
  size?: IconSizeNames | undefined
}>()
</script>

<template>
  <CmkIcon
    v-if="props.spec.type === 'default_icon'"
    :name="props.spec.id as SimpleIcons"
    :size="size"
  />
  <div v-else-if="props.spec.type === 'user_icon'">
    <img :src="props.spec.path" :width="iconSize" :height="iconSize" />
  </div>
  <div v-else>{{ untranslated('ERROR') }}</div>
</template>
