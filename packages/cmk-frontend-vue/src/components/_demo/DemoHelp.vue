<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import HelpText from '../HelpText.vue'

const lorem = `
Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Nullam mattis magna a felis semper feugiat. Integer mollis,
velit ornare mollis vehicula, ex enim tempor nibh, ac
bibendum elit velit et quam. Nulla sed eleifend nibh.
Quisque volutpat risus eget nisl gravida porttitor. Proin
bibendum, enim quis euismod accumsan, nunc urna condimentum
nulla, in fermentum nunc purus eu nisl. In malesuada, magna
vel facilisis rhoncus, sem libero porta odio, ac venenatis
tortor urna vel nulla. Nunc elementum mattis auctor. Donec
sagittis at nunc vel rutrum. Maecenas quis ultrices mi. Duis
semper blandit quam ut varius. Nam luctus neque nec magna
interdum, sit amet consectetur velit rhoncus. Suspendisse
ultrices neque in nulla ultrices, in tempor velit commodo.
Integer congue dui at metus imperdiet, quis cursus magna blandit.`

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <p>help <HelpText help="This is a demo help text." /></p>
  <p>
    long help
    <HelpText :help="`${Array.from({ length: 10 }, () => `<p>${lorem}</p>`).join('')}`" />
  </p>
</template>

<style scoped></style>
