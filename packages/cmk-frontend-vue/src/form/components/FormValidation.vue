<script setup lang="ts">
const props = defineProps<{
  validation: Array<string>
}>()
</script>

<template>
  <div v-if="props.validation.length > 0" class="validation">
    <ul>
      <li v-for="message in props.validation" :key="message" style="background: #ff5e5e">
        {{ message }}
      </li>
    </ul>
  </div>
</template>
