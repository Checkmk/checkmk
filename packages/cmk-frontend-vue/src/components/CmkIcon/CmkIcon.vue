<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watchEffect } from 'vue'

import { useTheme } from '@/lib/useTheme.ts'

import { cmkIconVariants } from './icons.constants.ts'
import type { CmkIconProps } from './types.ts'
import { getIconPath } from './utils.ts'

const props = defineProps<CmkIconProps>()
const { theme } = useTheme()

const iconSrc = ref('')

watchEffect((onCleanup) => {
  let isCancelled = false
  onCleanup(() => {
    isCancelled = true
  })

  const fetchIcon = async () => {
    const path = await getIconPath(props.name, theme.value)

    if (!isCancelled) {
      iconSrc.value = path
    }
  }
  void fetchIcon()
})

const getTransformRotate = () => {
  return `rotate(${props.rotate || 0}deg)`
}
</script>

<template>
  <img
    class="cmk-icon"
    :class="[
      cmkIconVariants({
        variant: props.variant,
        colored: props.colored,
        size: props.size || 'medium'
      }),
      { png: iconSrc.endsWith('.png') }
    ]"
    :src="iconSrc"
    :title="title || ''"
    :alt="title || ''"
  />
</template>

<style scoped>
.cmk-icon {
  margin: 0;
  padding: 0;
  vertical-align: baseline;
  transform: v-bind('getTransformRotate()');

  &.cmk-icon--inline {
    display: inline-block;
    margin-right: var(--spacing-half);
    vertical-align: middle;
  }

  &.cmk-icon--colorless {
    filter: grayscale(100%);
  }
}

.cmk-icon--xxsmall {
  width: 8px;
  height: 8px;
}

.cmk-icon--xsmall {
  width: 10px;
  height: 10px;
}

.cmk-icon--small {
  width: 12px;
  height: 12px;
}

.cmk-icon--medium {
  width: 15px;
  height: 15px;
}

.cmk-icon--large {
  width: 18px;
  height: 18px;
}

.cmk-icon--xlarge {
  width: 20px;
  height: 20px;
}

.cmk-icon--xxlarge {
  width: 32px;
  height: 32px;
}

.cmk-icon--xxxlarge {
  width: 77px;
  height: 77px;
}
</style>
