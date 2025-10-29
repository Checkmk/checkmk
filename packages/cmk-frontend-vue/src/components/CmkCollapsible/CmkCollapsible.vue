<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

interface CmkCollapsibleProps {
  open: boolean
  contentId?: string | undefined
}

const props = defineProps<CmkCollapsibleProps>()

const contentRef = ref<HTMLElement | null>(null)
const heightCSS = ref<string>('auto')

watch(
  () => [props.open, contentRef.value],
  async () => {
    await nextTick()
    if (contentRef.value) {
      // Temporarily disable transitions and animations to get the correct height
      const currentTransitionDuration = contentRef.value.style.transitionDuration
      const currentAnimationName = contentRef.value.style.animationName
      contentRef.value.style.transitionDuration = '0ms'
      contentRef.value.style.animationName = 'none'

      const height = contentRef.value.getBoundingClientRect().height
      heightCSS.value = `${height}px`

      // Re-enable transitions and animations
      contentRef.value.style.transitionDuration = currentTransitionDuration
      contentRef.value.style.animationName = currentAnimationName
    }
  },
  { immediate: true }
)
</script>

<template>
  <Transition name="content">
    <div v-show="open" :id="contentId" ref="contentRef">
      <slot />
    </div>
  </Transition>
</template>

<style scoped lang="scss">
.content-enter-active {
  animation: slideDown 300ms ease-out;
  overflow: hidden;
}

.content-leave-active {
  animation: slideUp 300ms ease-out;
  overflow: hidden;
}

@mixin zero-height {
  height: 0;
  opacity: 0;
}

@mixin full-height {
  height: v-bind('heightCSS');
  opacity: 1;
}

@keyframes slideDown {
  from {
    @include zero-height;
  }
  to {
    @include full-height;
  }
}

@keyframes slideUp {
  from {
    @include full-height;
  }
  to {
    @include zero-height;
  }
}
</style>
