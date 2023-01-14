import {AbstractLink, link_type_class_registry} from "nodevis/link_utils";

export class DefaultLinkNode extends AbstractLink {
    static class_name = "default";
}

link_type_class_registry.register(DefaultLinkNode);
