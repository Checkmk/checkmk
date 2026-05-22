<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch } from 'vue'

const model = defineModel<string[]>({ required: true })

function format(arr: string[]): string {
  return arr.join('\n')
}

function parse(raw: string): string[] {
  return raw
    .split('\n')
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

const raw = ref(format(model.value))

watch(model, (newVal) => {
  if (JSON.stringify(parse(raw.value)) !== JSON.stringify(newVal)) {
    raw.value = format(newVal)
  }
})

function onInput(event: Event) {
  raw.value = (event.target as HTMLTextAreaElement).value
  model.value = parse(raw.value)
}
</script>

<template>
  <textarea
    rows="3"
    class="ucl-string-array-textarea__textarea"
    :value="raw"
    @input="onInput"
  ></textarea>
</template>

<style scoped>
.ucl-string-array-textarea__textarea {
  flex: 1;
}
</style>
