<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon, { type CmkIconProps } from 'cmk-ui-library/components/CmkIcon'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import type {
  CmkMultitoneIconColor,
  CmkMultitoneIconNames,
  CustomIconColor,
  IconSizeNames
} from 'cmk-ui-library/components/CmkIcon/types'
import { computed, useTemplateRef } from 'vue'

/** A themed bitmap icon. `primaryColor` is what picks the multitone branch, so it must stay unset. */
interface RasterIconButtonProps extends CmkIconProps {
  primaryColor?: undefined
  secondaryColor?: undefined
}

/**
 * An inline multitone SVG. Requiring the color here is what keeps the names that exist only as
 * multitone assets - 'more-actions', 'success', … - out of the raster branch, where they would
 * resolve to no image at all.
 */
interface MultitoneIconButtonProps {
  name: CmkMultitoneIconNames
  // NonNullable, so that `primaryColor === undefined` tells the two branches apart: the cva-derived
  // color type admits `undefined` on its own and would blur the discriminant.
  primaryColor: NonNullable<CmkMultitoneIconColor> | CustomIconColor
  secondaryColor?: CmkMultitoneIconColor | CustomIconColor | undefined
  size?: IconSizeNames | undefined
  rotate?: number | undefined
  title?: string | undefined
  variant?: undefined
  colored?: undefined
}

const props = defineProps<RasterIconButtonProps | MultitoneIconButtonProps>()

defineEmits(['click'])

const button = useTemplateRef<HTMLButtonElement>('button')

const multitone = computed<MultitoneIconButtonProps | null>(() =>
  props.primaryColor === undefined ? null : props
)

const raster = computed<RasterIconButtonProps | null>(() =>
  props.primaryColor === undefined ? props : null
)

defineExpose({
  focus: () => {
    button.value?.focus()
  }
})
</script>

<template>
  <button
    ref="button"
    type="button"
    class="cmk-icon-button"
    :title="title"
    @click.prevent="
      (e) => {
        $emit('click', e)
      }
    "
  >
    <CmkMultitoneIcon
      v-if="multitone"
      :name="multitone.name"
      :primary-color="multitone.primaryColor"
      :secondary-color="multitone.secondaryColor"
      :size="multitone.size"
      :rotate="multitone.rotate"
      :title="multitone.title"
    />
    <CmkIcon
      v-else-if="raster"
      :name="raster.name"
      :variant="raster.variant"
      :size="raster.size"
      :colored="raster.colored"
      :rotate="raster.rotate"
      :title="raster.title"
    />
  </button>
</template>

<style scoped>
.cmk-icon-button {
  margin: 0;
  padding: 0;
  background: none;
  border: none;
  cursor: pointer;

  /* Collapse the inline-image baseline descender gap so the focus outline
     hugs the icon instead of leaving a strip below it. */
  display: inline-flex;
}

.cmk-icon-button:focus-visible {
  outline: revert;
}

/* Mirrors CmkButton, so a disabled icon button does not read as an enabled one. */
.cmk-icon-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
