import metrics
import sites
import config


class GrafanaConnectorMetrics(APICallCollection):
    def get_api_calls(self):
        return {
            "get_user_sites": {
                "handler": self._get_user_sites,
                "locking": False,
            },
            "get_host_names": {
                "handler": self._get_host_names,
                "locking": False,
            },
            "get_metrics_of_host": {
                "handler": self._get_metrics_of_host,
                "locking": False,
            },
            "get_graph_recipes": {
                "handler": self._get_graph_recipes,
                "locking": False,
            },
        }

    def _get_user_sites(self, request):
        return config.sorted_sites()

    def _get_host_names(self, request):
        validate_request_keys(request, optional_keys=["site_id"])
        return self._query_for_host_names(request.get("site_id"))

    def _query_for_host_names(self, site_id):
        try:
            sites.live().set_only_sites([site_id] if site_id else None)
            return sites.live().query_column("GET hosts\nColumns: name\n")
        finally:
            sites.live().set_only_sites(None)

    def _get_metrics_of_host(self, request):
        validate_request_keys(request, required_keys=["hostname"], optional_keys=["site_id"])
        return self._query_for_metrics_of_host(request["hostname"], request.get("site_id"))

    def _query_for_metrics_of_host(self, host_name, site_id):
        if not host_name:
            return []

        query = ("GET services\n"
                 "Columns: description check_command metrics\n"
                 "Filter: host_name = %s\n" % lqencode(host_name))

        response = {}

        try:
            sites.live().set_only_sites([site_id] if site_id else None)
            rows = sites.live().query(query)
        finally:
            sites.live().set_only_sites(None)

        for service_description, check_command, metrics in rows:
            response[service_description] = {
                "check_command": check_command,
                "metrics": self._get_metric_infos(metrics, check_command),
            }

        return response

    def _get_metric_infos(self, service_metrics, check_command):
        metric_infos = {}
        for nr, perfvar in enumerate(service_metrics):
            translated = metrics.perfvar_translation(nr, perfvar, check_command)
            name = translated["name"]
            mi = metrics.metric_info.get(name, {})
            metric_infos[perfvar] = {
                "index": nr,
                "name": name,
                "title": mi.get("title", name.title()),
            }
        return metric_infos

    def _get_graph_recipes(self, request):
        if not metrics.cmk_graphs_possible():
            raise MKGeneralException(_("Currently not supported with this Check_MK Edition"))
        _graph_data_range, graph_recipes = metrics.graph_recipes_for_api_request(request)
        return graph_recipes


api_actions.update(GrafanaConnectorMetrics().get_api_calls())
