

export class NodeVisualizationLayout {
    constructor(viewport) {
        this.id = null
        this.viewport = viewport
        this.reference_size = {}
        this.style_configs = []
        this.overlay_config = {}
    }

    save_style(style_config) {
        this.style_configs.push(style_config)
    }

    clear_styles() {
        this.style_configs = []
    }

    remove_style(style_instance) {
        let idx = this.style_configs.indexOf(style_instance.style_config)
        this.style_configs.splice(idx, 1)
    }

    serialize() {
        return {
            auto_align_mode: this.auto_align,
            description: this.description,
            reference_size: this.reference_size,
            style_configs: this.style_configs,
            overlay_config: this.overlay_config,
        }
    }

    deserialize(data) {
        this.id = data.id
        this.reference_size = data.reference_size
        this.style_configs  = data.style_configs
        this.overlay_config = data.overlay_config
    }
}
