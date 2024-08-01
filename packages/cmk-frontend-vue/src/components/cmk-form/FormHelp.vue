<script setup lang="ts">
defineProps<{
  help: string
}>()
// TODO: do not use v-html. parse string, keep certain tags
</script>

<template>
  <div v-if="help" class="help vue_help">
    <div class="info_icon">
      <img class="icon" />
    </div>
    <!-- eslint-disable vue/no-v-html -->
    <div class="help_text" v-html="help" />
  </div>
</template>
