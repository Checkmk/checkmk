<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from './CmkIcon.vue'
import type { IconEmblems, SimpleIcons } from './types'
import { type CmkIconProps } from './types'

defineProps<{
  size: CmkIconProps['size']
  icon: SimpleIcons
  iconEmblem: IconEmblems | undefined
}>()
</script>

<template>
  <div class="cmk-icon-with-emblem__root">
    <div class="cmk-icon-with-emblem__wrapper">
      <CmkIcon :name="icon" :size="size" />
      <div v-if="iconEmblem">
        <img
          :class="['cmk-icon-with-emblem__emblem', `cmk-icon-with-emblem__emblem--${iconEmblem}`]"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.cmk-icon-with-emblem__root {
  display: flex;
}

.cmk-icon-with-emblem__wrapper {
  position: relative;
  flex-shrink: 0;
}

.cmk-icon-with-emblem__emblem {
  width: 68%;
  height: 68%;
  position: absolute;
  right: -15%;
  bottom: -7%;
}
</style>

<style lang="scss">
$emblems_themed:
  add, api, disable, download, enable, more, pending, refresh, rulesets, search, settings,
  statistic, time, warning;

$emblems: downtime, edit, sign, trans;

@each $emblem in $emblems_themed {
  body[data-theme='modern-dark'] {
    .cmk-icon-with-emblem__emblem--#{$emblem} {
      content: url('~cmk-frontend/themes/modern-dark/images/emblem_#{$emblem}.svg');
    }
  }

  body[data-theme='facelift'] {
    .cmk-icon-with-emblem__emblem--#{$emblem} {
      content: url('~cmk-frontend/themes/facelift/images/emblem_#{$emblem}.svg');
    }
  }
}

@each $emblem in $emblems {
  .cmk-icon-with-emblem__emblem--#{$emblem} {
    content: url('~cmk-frontend/themes/facelift/images/emblem_#{$emblem}.svg');
  }
}

.cmk-icon-with-emblem__emblem--remove {
  content: url('~cmk-frontend/themes/facelift/images/emblem_remove.png');
}
</style>
