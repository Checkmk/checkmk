<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { extract_value, type ValueAndValidation } from '@/types'
import type { VueLegacyValuespec } from '@/vue_types'

const emit = defineEmits<{
  (e: 'update-value', value: unknown): void
}>()

interface LegacyWrapper {
  varprefix: string
  html: string
}

const props = defineProps<{
  vueSchema: VueLegacyValuespec
  data: ValueAndValidation<LegacyWrapper>
}>()

const legacy_dom = ref<HTMLFormElement | undefined>()
function emit_form() {
  emit('update-value', {
    input_context: Object.fromEntries(new FormData(legacy_dom.value)),
    varprefix: extract_value(props.data).varprefix
  })
}

onMounted(() => {
  const observer = new MutationObserver(() => {
    emit_form()
  })
  if (legacy_dom.value === undefined) {
    throw Error('can not observe legacy_dom is null')
  }
  observer.observe(legacy_dom.value, {
    subtree: true,
    childList: true,
    attributes: true
  })
})
</script>

<template>
  <!-- eslint-disable vue/no-v-html -->
  <form
    ref="legacy_dom"
    style="background: #595959"
    class="legacy_valuespec"
    v-html="extract_value(data).html"
  ></form>
  <!-- eslint-enable -->
</template>
