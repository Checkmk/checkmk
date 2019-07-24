import * as node_visualization_layout from "node_visualization_layout"


export class LayoutStyleFactory {
    constructor(layout_manager) {
        this.layout_manager = layout_manager
        this.style_templates = {}
        this.load_styles()
    }

    load_styles() {
        LayoutStyleFactory.style_classes.forEach(style=>{
            this.style_templates[style.prototype.type()] = style
        })
    }

    get_styles(){
        return this.style_templates
    }

    get_style_class(style_config) {
        return this.style_templates[style_config.type]
    }

    get_default_style_config(style_name, node) {

    }

    // Creates a style instance with the given style_config
    instantiate_style(style_config, node, selection) {
        return new (this.get_style_class(style_config))(this.layout_manager, style_config, node, selection)
    }

    instantiate_style_name(style_name, node, selection) {
        return this.instantiate_style({type: style_name}, node, selection)
    }

    instantiate_style_class(style_class, node, selection) {
        return this.instantiate_style({type: style_class.prototype.type()}, node, selection)
    }
}

LayoutStyleFactory.style_classes = []
