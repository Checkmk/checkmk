
export class LayeredLayerBase {
    constructor(viewport, enabled=true) {
        this.toggleable = false
        this.enabled = enabled
        this.viewport = viewport
        this.selection = null
    }


    // Initialize GUI elements and objects
    // Does not process/store any external data

    // Shows the layer
    enable(layer_selections) {
        this.enabled = true
        this.selection = layer_selections.svg
        this.div_selection = layer_selections.div

        // Setup components
        this.setup()
        // Scale to size
        this.size_changed()

        // Without data simply return
        if (this.viewport.get_all_nodes().length == 0)
            return

        // Adjust zoom
        this.zoomed()
        // Update data references
        this.update_data()
        // Update gui
        this.update_gui()
    }

    disable() {
        this.enabled = false

        if (this.selection) {
            this.selection.selectAll("*").remove()
            this.selection = null
        }

        if (this.div_selection) {
            this.div_selection.selectAll("*").remove()
            this.div_selection = null
        }
    }

    setup() {}

    // Called when the viewport size has changed
    size_changed() {}

    zoomed() {}

    set_enabled(is_enabled) {
        this.enabled = is_enabled
        if (this.enabled)
            this.viewport.enable_layer(this.id())
        else
            this.viewport.disable_layer(this.id())
    }

    is_enabled() {
        return this.enabled
    }

    is_toggleable() {
        return this.toggleable
    }

    update_data() {}

    update_gui() {}

}

export class LayeredOverlayBase extends LayeredLayerBase {
    constructor(viewport, enabled=true) {
        super(viewport, enabled)
        this.toggleable = true
    }
}
