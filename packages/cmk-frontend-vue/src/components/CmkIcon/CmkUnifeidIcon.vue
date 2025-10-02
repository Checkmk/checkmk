<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from './CmkIcon.vue'
import CmkMultitoneIcon from './CmkMultitoneIcon.vue'
import { oneColorIcons, simpleIcons, twoColorIcons } from './icons.constants.ts'
import type { CmkAllIconProps, OneColorIcons, SimpleIcons, TwoColorIcons } from './types.ts'

const props = defineProps<CmkAllIconProps>()
</script>

<template>
  <!--< this handles the case like 'services' where there is both a simple icon and multitone icon.
    this should be thought through more for the future. defaulting to a simple icon is temporary.
    />-->

  <CmkIcon
    v-if="simpleIcons.includes(props.name as SimpleIcons)"
    :name="props.name as SimpleIcons"
    :size="props.size"
    :title="props.title"
    :rotate="props.rotate"
    :variant="'variant' in props ? props.variant : undefined"
    :colored="'colored' in props ? props.colored : undefined"
  />

  <CmkMultitoneIcon
    v-else-if="oneColorIcons.includes(props.name as OneColorIcons)"
    :name="props.name as OneColorIcons"
    :size="props.size"
    :title="props.title"
    :rotate="props.rotate"
    :primary-color="'primaryColor' in props ? props.primaryColor : undefined"
  />

  <CmkMultitoneIcon
    v-else-if="twoColorIcons.includes(props.name as TwoColorIcons)"
    :name="props.name as TwoColorIcons"
    :size="props.size"
    :title="props.title"
    :rotate="props.rotate"
    :primary-color="'primaryColor' in props ? props.primaryColor : undefined"
    :secondary-color="'secondaryColor' in props ? props.secondaryColor : undefined"
  />
</template>
