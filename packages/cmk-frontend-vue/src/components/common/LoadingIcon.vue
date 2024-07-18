<script setup lang="ts">
interface LoadingIconProps {
  /** @property {number} height - Height of the loading icon */
  height?: number
}

const DEFAULT_HEIGHT = 32

withDefaults(defineProps<LoadingIconProps>(), {
  height: DEFAULT_HEIGHT
})
</script>

<template>
  <img
    :height="height || DEFAULT_HEIGHT"
    src="themes/facelift/images/load_graph.png"
    alt="Loading"
    aria-label="Loading"
  />
</template>
