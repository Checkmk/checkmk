<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
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
import { computed } from 'vue'

/** A themed bitmap icon. `primaryColor` is what picks the multitone branch, so it must stay unset. */
export interface RasterIconProps extends CmkIconProps {
  primaryColor?: undefined
  secondaryColor?: undefined
}

/**
 * An inline multitone SVG. Requiring the color here is what keeps the names that exist only as
 * multitone assets - 'more-actions', 'success', … - out of the raster branch, where they would
 * resolve to no image at all.
 */
export interface MultitoneIconProps {
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

export type AutoIconProps = RasterIconProps | MultitoneIconProps

const props = defineProps<AutoIconProps>()

const multitone = computed<MultitoneIconProps | null>(() =>
  props.primaryColor === undefined ? null : props
)

const raster = computed<RasterIconProps | null>(() =>
  props.primaryColor === undefined ? props : null
)
</script>

<template>
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
</template>
