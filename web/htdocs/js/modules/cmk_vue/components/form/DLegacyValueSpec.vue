<script setup lang="ts">
import {ref, onMounted, onBeforeMount} from "vue";
import {VueComponentSpec} from "cmk_vue/types";

// TODO: correct handling of inline html <i></i>. For example VMware ESX via vSphere / 'additionally'
interface VueLegacyValuespecComponentSpec extends VueComponentSpec {
    config: {
        html: string;
        varprefix: string;
    };
}

const props = defineProps<{
    component: VueLegacyValuespecComponentSpec;
}>();

const legacy_dom = ref<HTMLFormElement | undefined>();

onBeforeMount(() => {});

function collect(): any {
    let result = Object.fromEntries(new FormData(legacy_dom.value));
    return {input_context: result, varprefix: props.component.config.varprefix};
}

function debug_info(): void {
    console.log("Some legacy valuespec");
}

defineExpose({
    collect,
    debug_info,
});
</script>

<template>
    <form
        style="background: #595959"
        class="legacy_valuespec"
        v-html="component.config.html"
        ref="legacy_dom"
    ></form>
</template>
