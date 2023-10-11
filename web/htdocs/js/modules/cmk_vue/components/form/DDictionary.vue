<script setup lang="ts">
import {onMounted, ref} from "vue";
import {IComponent, VueComponentSpec} from "cmk_vue/types";
import DForm from "./DForm.vue";

interface VueDictionaryKeySpec {
    name: string;
    optional: boolean;
}

interface VueDictionaryComponentSpec extends VueComponentSpec {
    config: {
        elements: {
            key_spec: VueDictionaryKeySpec;
            is_active: boolean;
            component: VueComponentSpec;
        }[];
    };
}

const props = defineProps<{
    component: VueDictionaryComponentSpec;
}>();

const formElements = ref<{[index: string]: IComponent}>({});
const formElementActive: {[index: string]: any} = ref({});

onMounted(() => {
    props.component.config.elements.forEach(element => {
        if (element.is_active || !element.key_spec.optional)
            formElementActive.value[element.key_spec.name] = true;
    });
});

function collect(): any {
    let result: {[index: string]: any} = {};
    for (let element of get_elements_from_props()) {
        const component = formElements.value[element.key_spec.name];
        if (component == undefined) continue;
        result[element.key_spec.name] = component.collect();
    }
    return result;
}

function debug_info(): void {
    console.log(
        "Dictionary with ",
        Object.keys(props.component.config.elements).length,
        "keys"
    );
}

defineExpose({
    collect,
    debug_info,
});

function get_elements_from_props(): {
    key_spec: VueDictionaryKeySpec;
    component: VueComponentSpec;
}[] {
    return props.component.config.elements;
}
</script>
<template>
    <table class="dictionary">
        <tbody>
            <tr
                v-for="element in get_elements_from_props()"
                v-bind:key="element.key_spec.name"
            >
                <td class="dictleft">
                    <span>
                        <input
                            type="checkbox"
                            class="vue_checkbox"
                            v-model="formElementActive[element.key_spec.name]"
                            v-if="element.key_spec.optional"
                        />
                        <label>{{ element.component.title }}</label>
                    </span>
                    <br />
                    <div class="dictelement indent">
                        <DForm
                            v-if="formElementActive[element.key_spec.name]"
                            :component="element.component"
                            :ref="
                                el => {
                                    formElements[element.key_spec.name] = el;
                                }
                            "
                        />
                    </div>
                </td>
            </tr>
        </tbody>
    </table>
</template>
