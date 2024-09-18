<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type NoteTextWidgetProps } from './widget_types'

defineProps<NoteTextWidgetProps>()
</script>

<template>
  <p>{{ text }}</p>
</template>

<style scoped></style>
