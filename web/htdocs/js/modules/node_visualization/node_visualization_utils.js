
export class DefaultTransition {
    static duration() {
        return 500;
    }

    static add_transition(selection) {
        return selection.transition().duration(DefaultTransition.duration())
    }
}


export class NodeMatcher {
    constructor(hierarchy_list) {
        this.hierarchy_list = hierarchy_list
    }

    find_node(matcher) {
        let nodes_to_check = []

        if (matcher.rule_id)
            nodes_to_check =  this._get_aggregator_nodes()
        else if(matcher.hostname || matcher.service)
            nodes_to_check =  this._get_leaf_nodes()
        else
            nodes_to_check =  this._get_all_nodes()

        for (let idx in nodes_to_check) {
            let node = nodes_to_check[idx]
            if (this._match_node(matcher, node))
                return node
        }
    }

    _get_all_nodes() {
        let all_nodes = []
        this.hierarchy_list.forEach(partition=>{
            all_nodes = all_nodes.concat(partition.nodes)
        })
        return all_nodes
    }

    _get_aggregator_nodes() {
        let aggregator_nodes = []
        this.hierarchy_list.forEach(partition=>{
            partition.nodes.forEach(node=>{
                if (node.children)
                    aggregator_nodes.push(node)
            })
        })
        return aggregator_nodes
    }

    _get_leaf_nodes() {
        let leaf_nodes = []
        this.hierarchy_list.forEach(partition=>{
            partition.nodes.forEach(node=>{
                if (!node._children)
                    leaf_nodes.push(node)
            })
        })
        return leaf_nodes
    }

    _match_node(matcher, node) {
        // Basic matches
        let elements = ["hostname", "service"]
        for (let idx in elements) {
            let match_type = elements[idx]
            if (matcher[match_type] && !matcher[match_type].disabled && node.data[match_type] != matcher[match_type].value)
                return false
        }

        // List matches
        elements = ["aggr_path_id", "aggr_path_name"]
        for (let idx in elements) {
            let match_type = elements[idx]
            if (!matcher[match_type])
                continue

            if (matcher[match_type].disabled)
                continue

            if (JSON.stringify(matcher[match_type].value) != JSON.stringify(node.data[match_type]))
                return false
        }

        // Complex matches
        if (matcher.rule_id && !matcher.rule_id.disabled && node.data.rule_id.rule != matcher.rule_id.value)
            return false

        // Complex matches
        if (matcher.rule_name && !matcher.rule_name.disabled && node.data.name != matcher.rule_name.value)
            return false


        return node
    }
}

