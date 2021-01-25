import * as cmk_figures from "cmk_figures";
import * as cmk_site_overview from "cmk_site_overview";

class AlertStatistics extends cmk_site_overview.SiteOverview {
    static ident() {
        return "alert_statistics";
    }
}

cmk_figures.figure_registry.register(AlertStatistics);
