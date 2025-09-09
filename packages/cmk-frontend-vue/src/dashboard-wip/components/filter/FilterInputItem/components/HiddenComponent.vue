<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { HiddenConfig } from '../../types.ts'
import type { ComponentEmits, FilterComponentProps } from './types.ts'

const props = defineProps<FilterComponentProps<HiddenConfig>>()
const emit = defineEmits<ComponentEmits>()

if (props.configuredValues === null) {
  emit('update-component-values', props.component.id, {
    [props.component.id]: props.component.value
  })
}
</script>

<template>
  <div />
</template>
