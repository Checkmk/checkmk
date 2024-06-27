<script setup lang="ts">
type InlineChevronVariant = 'bottom' | 'left' | 'right'

interface InlineChevronProps {
  variant: InlineChevronVariant
}

defineProps<InlineChevronProps>()
</script>

<template>
  <span :class="['chevron', variant]" />
</template>

<style scoped>
.chevron::before {
  border-color: #13d389;
  border-style: solid;
  border-width: 0.25em 0.25em 0 0;
  content: '';
  display: inline-block;
  height: 0.45em;
  left: 0.15em;
  position: relative;
  top: 0.15em;
  transform: rotate(-45deg);
  vertical-align: top;
  width: 0.45em;
}

.chevron.right:before {
  left: 0;
  transform: rotate(45deg);
  transition: transform 100ms linear;
}

.chevron.bottom:before {
  top: 0;
  transform: rotate(135deg);
  transition: transform 100ms linear;
}

.chevron.left:before {
  left: 0.25em;
  transform: rotate(-135deg);
  transition: transform 100ms linear;
}
</style>
