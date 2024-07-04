<script setup lang="ts">
interface StepNumberProps {
  /** @property {number} number - The number to display in the step */
  number: number

  /** @property {boolean} active - If true, the step is currently active */
  active: boolean

  /** @property {boolean} complete - If true, the step is complete */
  complete: boolean
}

defineProps<StepNumberProps>()
</script>

<template>
  <span
    class="cmk-stepper__number"
    :class="{
      active: active,
      complete: complete
    }"
    >{{ number }}</span
  >
</template>

<style scoped>
.cmk-stepper__number.active,
.cmk-stepper__number.complete {
  color: white;
}

.cmk-stepper__number {
  z-index: 1;
  position: relative;
  font-size: large;
  font-weight: bold;
  left: -2.9rem;
  top: -0.3rem;
  color: black;
}
</style>
