//types from: cmk/gui/cee/plugins/dashboard/site_overview.py a
//TODO: this is kind of code duplication, since the types are defined twice
// in python and typescript, so maybe in the future it would be better to have
// a way to automatically generate them from one sie to another
export interface ABCElement {
    title: string;
    tooltip: string;
}

export interface SiteElement extends ABCElement {
    url_add_vars: Record<string, string>;
    total: Part;
    parts: Part[];
}

export interface HostElement extends ABCElement {
    link: string;
    host_css_class: string;
    service_css_class: string;
    has_host_problem: boolean;
    num_services: number;
    num_problems: number;
}

export interface IconElement extends ABCElement {
    css_class: string;
}

export interface Part {
    title: string;
    css_class: string;
    count: number;
}
