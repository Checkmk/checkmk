from typing import Any, Callable

from cmk.gui.form_specs.private import UnknownFormSpec
from cmk.gui.form_specs.vue.visitors._base import FormSpecVisitor
from cmk.gui.form_specs.vue.visitors._type_defs import VisitorOptions
from cmk.gui.utils.rule_specs.loader import LoadedRuleSpec

from cmk.rulesets.v1.form_specs import FormSpec
from cmk.rulesets.v1.form_specs._base import ModelT

form_spec_registry: dict[str, LoadedRuleSpec] = {}
RecomposerFunction = Callable[[FormSpec[Any]], FormSpec[Any]]
form_specs_visitor_registry: dict[
    type[FormSpec[Any]], tuple[type[FormSpecVisitor[FormSpec[Any], Any]], RecomposerFunction | None]
] = {}


def register_visitor_class(
    form_spec_class: type[FormSpec[ModelT]],
    visitor_class: type[FormSpecVisitor[Any, ModelT]],
    recomposer: RecomposerFunction | None = None,
) -> None:
    form_specs_visitor_registry[form_spec_class] = (visitor_class, recomposer)


def get_visitor(
    form_spec: FormSpec[ModelT], options: VisitorOptions
) -> FormSpecVisitor[FormSpec[ModelT], ModelT]:
    if registered_form_spec := form_specs_visitor_registry.get(form_spec.__class__):
        visitor, recomposer_function = registered_form_spec
        if recomposer_function is not None:
            form_spec = recomposer_function(form_spec)
            return get_visitor(form_spec, options)
        return visitor(form_spec, options)

    # If the form spec has no valid visitor, convert it to the legacy valuespec visitor
    visitor, unknown_decomposer = form_specs_visitor_registry[UnknownFormSpec]
    assert unknown_decomposer is not None
    return visitor(unknown_decomposer(form_spec), options)
