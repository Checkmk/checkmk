<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { extract_value, type ValueAndValidation } from '@/types'
import type { VueLegacyValuespec } from '@/vue_types'

const emit = defineEmits<{
  (e: 'update-value', value: any): void
}>()

const props = defineProps<{
  vue_schema: VueLegacyValuespec
  data: ValueAndValidation
}>()

const legacy_dom = ref<HTMLFormElement | undefined>()
function emit_form(): any {
  emit('update-value', {
    input_context: Object.fromEntries(new FormData(legacy_dom.value)),
    varprefix: extract_value(props.data).varprefix
  })
}

onMounted(() => {
  const observer = new MutationObserver((mutationList, observer) => {
    emit_form();
  })
  observer.observe(legacy_dom.value, {
    subtree: true,
    childList: true,
    attributes: true
  })
})
</script>

<template>
  <form
    style="background: #595959"
    class="legacy_valuespec"
    v-html="extract_value(data).html"
    ref="legacy_dom"
  ></form>
</template>
