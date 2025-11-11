<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <CmkScrollContainer :max-height="'160px'">
    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam mattis magna a felis semper
    feugiat. Integer mollis, velit ornare mollis vehicula, ex enim tempor nibh, ac bibendum elit
    velit et quam. Nulla sed eleifend nibh. Quisque volutpat risus eget nisl gravida porttitor.
    Proin bibendum, enim quis euismod accumsan, nunc urna condimentum nulla, in fermentum nunc purus
    eu nisl. In malesuada, magna vel facilisis rhoncus, sem libero porta odio, ac venenatis tortor
    urna vel nulla. Nunc elementum mattis auctor. Donec sagittis at nunc vel rutrum. Maecenas quis
    ultrices mi. Duis semper blandit quam ut varius. Nam luctus neque nec magna interdum, sit amet
    consectetur velit rhoncus. Suspendisse ultrices neque in nulla ultrices, in tempor velit
    commodo. Integer congue dui at metus imperdiet, quis cursus magna blandit.Lorem ipsum dolor sit
    amet, consectetur adipiscing elit. Nullam mattis magna a felis semper feugiat. Integer mollis,
    velit ornare mollis vehicula, ex enim tempor nibh, ac bibendum elit velit et quam. Nulla sed
    eleifend nibh. Quisque volutpat risus eget nisl gravida porttitor. Proin bibendum, enim quis
    euismod accumsan, nunc urna condimentum nulla, in fermentum nunc purus eu nisl. In malesuada,
    magna vel facilisis rhoncus, sem libero porta odio, ac venenatis tortor urna vel nulla. Nunc
    elementum mattis auctor. Donec sagittis at nunc vel rutrum. Maecenas quis ultrices mi. Duis
    semper blandit quam ut varius. Nam luctus neque nec magna interdum, sit amet consectetur velit
    rhoncus. Suspendisse ultrices neque in nulla ultrices, in tempor velit commodo. Integer congue
    dui at metus imperdiet, quis cursus magna blandit.
  </CmkScrollContainer>
</template>
