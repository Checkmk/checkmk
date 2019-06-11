
export class ToolbarPluginBase extends Object {
    static id() {}

    constructor(description, main_instance) {
        super()
        this.main_instance = main_instance
        this.description = description
        this.active = false
        this.togglebutton_selection = null
        this.content_selection = null
    }

    setup_selections(togglebutton_selection, content_selection) {
        this.togglebutton_selection = togglebutton_selection
        this.content_selection = content_selection
    }

    toggle_active() {
        this.active = !this.active
        this.update_active_state()
    }

    update_active_state() {
        if (!this.active) {
            if (this.togglebutton_selection) {
                this.togglebutton_selection.classed("on", false)
                this.togglebutton_selection.classed("off", true)
                this.togglebutton_selection.classed("up", false)
                this.togglebutton_selection.classed("down", true)
            }
            this.disable_actions()
            this.remove()
        }
        else {
            if (this.togglebutton_selection) {
                this.togglebutton_selection.classed("on", true)
                this.togglebutton_selection.classed("off", false)
                this.togglebutton_selection.classed("up", true)
                this.togglebutton_selection.classed("down", false)
            }
            this.enable_actions()
            this.render_content()
        }
    }

    remove() {
        this.content_selection.selectAll("*").remove()
    }

    has_toggle_button() {
        return true
    }

    render_togglebutton() {}

    render_content() {}

    description() {
        return this.description
    }

    enable() {
        this.active = true
        this.enable_actions()
    }

    enable_actions() {}

    disable() {
        this.active = false
        this.disable_actions()
    }

    disable_actions() {}
}

