<script setup lang="ts">
import { type NoteTextWidgetProps } from './widget_types'

defineProps<NoteTextWidgetProps>()
</script>

<template>
  <p>{{ text }}</p>
</template>

<style scoped></style>
