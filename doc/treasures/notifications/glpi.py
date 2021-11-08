#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Create/Update/Remove GLPI Ticket
# Bulk: No

import ast
import logging
import os
import re
import time
from socket import AF_UNIX, SHUT_WR, SOCK_STREAM, socket

log = logging.getLogger("ticket_log")

#.
#   .--Incident------------------------------------------------------------.
#   |                ___            _     _            _                   |
#   |               |_ _|_ __   ___(_) __| | ___ _ __ | |_                 |
#   |                | || '_ \ / __| |/ _` |/ _ \ '_ \| __|                |
#   |                | || | | | (__| | (_| |  __/ | | | |_                 |
#   |               |___|_| |_|\___|_|\__,_|\___|_| |_|\__|                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Incident(object):
    """
    stores the collected information about an incident, either from the
    event console or from a notification

    In the EventConsole case, the following variables have to be exported
    to the environment in the calling script:
    EC_ID, EC_PHASE, EC_HOST, EC_CONTACT, EC_TEXT, EC_STATE, EC_COMMENT
    """
    class Source(object):
        Notification, EventConsole = range(2)

    class What(object):
        Host, Service = range(2)

    class Type(object):
        Problem, Recovery, Flapping, FlappingStop, Acknowledgement, Other = range(6)

    def __init__(self, live_status):
        self.__source = None
        self.__what = None
        self.__type = Incident.Type.Other
        self.__host = None
        self.__service = None
        self.__message = None
        self.__state = None
        self.__contact = None
        self.__service_level = 0
        # cmk internal id where information about an incident is stored.
        # this is the event console id in the EC case or the id of a comment
        # for notifications
        self.__tracking_id = None
        self.__id = None
        self.__live_status = live_status

    @staticmethod
    def from_notification(env, live_status):
        res = Incident(live_status)
        res.__source = Incident.Source.Notification
        res.__host = env['NOTIFY_HOSTNAME']
        res.__contact = env['NOTIFY_CONTACTNAME']
        res.__time = time.strptime(env['NOTIFY_SHORTDATETIME'], "%Y-%m-%d %H:%M:%S")
        if env.get('NOTIFY_SERVICE_SL'):
            res.__service_level = int(env['NOTIFY_SERVICE_SL'])
        elif env.get('NOTIFY_HOST_SL'):
            res.__service_level = int(env['NOTIFY_HOST_SL'])
        else:
            res.__service_level = 0

        res.__type = {
            'PROBLEM': Incident.Type.Problem,
            'RECOVERY': Incident.Type.Recovery,
            'FLAPPINGSTART': Incident.Type.Flapping,
            'FLAPPINGSTOP': Incident.Type.FlappingStop,
            'ACKNOWLEDGEMENT': Incident.Type.Acknowledgement
        }.get(env['NOTIFY_NOTIFICATIONTYPE'], Incident.Type.Other)
        if res.__type == Incident.Type.Other:
            log.info("Unhandled notification type %s", env['NOTIFY_NOTIFICATIONTYPE'])

        if env['NOTIFY_WHAT'] == 'HOST':
            res.__what = Incident.What.Host
            res.__message = env['NOTIFY_HOSTOUTPUT']
            res.__state = env['NOTIFY_HOSTSTATE']
        else:
            res.__what = Incident.What.Service
            res.__message = env['NOTIFY_SERVICEOUTPUT']
            res.__state = env['NOTIFY_SERVICESTATE']
            res.__service = env['NOTIFY_SERVICEDESC']

        res.__tracking_id, res.__id = res.__retrieve_incident_id_notification()

        return res

    @staticmethod
    def from_event_console(env, live_status):
        res = Incident(live_status)
        res.__source = Incident.Source.EventConsole
        res.__what = Incident.What.Host
        res.__time = time.localtime()
        res.__tracking_id = env['EC_ID']
        res.__host = env['EC_HOST']
        res.__contact = env['EC_CONTACT']
        res.__message = env['EC_TEXT']
        res.__state = env['EC_STATE']
        res.__service_level = int(env.get('EC_SL', 0))
        res.__type = {
            'open': Incident.Type.Problem,
            'closed': Incident.Type.Recovery
        }.get(env['EC_PHASE'])

        res.__id = res.__retrieve_incident_id_ec(env['EC_COMMENT'])

        return res

    def __retrieve_incident_id_notification(self):
        comment_query = [
            "GET comments",
            "Columns: id comment",
            "Filter: host_name = %s" % self.host(),
        ]

        if self.service() is not None:
            comment_query.append("Filter: service_description = %s" % self.service())

        comments = self.__live_status.query_obj("\n".join(comment_query))
        for comment in comments:
            identifier = self.__parse_comment(comment[1])
            if identifier is not None:
                return comment[0], identifier
        return None, None

    def __store_incident_id_notification(self):
        now = int(time.time())
        if self.__service is not None:
            query = [
                "COMMAND [%s] ADD_SVC_COMMENT" % now, self.__host, self.__service, "1",
                self.__contact,
                self.__render_comment()
            ]
        else:
            query = [
                "COMMAND [%s] ADD_HOST_COMMENT" % now, self.__host, "1", self.__contact,
                self.__render_comment()
            ]
        self.__live_status.execute(";".join(query))
        log.debug("store ticket id: %s", ";".join(query))

    def __remove_incident_id_notification(self):
        now = int(time.time())
        log.debug("tracking id: %s", self.__tracking_id)
        if self.__service is not None:
            query = ["COMMAND [%s] DEL_SVC_COMMENT" % now, str(self.__tracking_id)]
        else:
            query = ["COMMAND [%s] DEL_HOST_COMMENT" % now, str(self.__tracking_id)]
        self.__live_status.execute(";".join(query))
        log.debug("remove ticket id: %s", ";".join(query))

    def __retrieve_incident_id_ec(self, comment):
        return self.__parse_comment(comment)

    def __store_incident_id_ec(self):
        query = [
            "COMMAND UPDATE", self.__tracking_id, self.__contact, "1",
            self.__render_comment(), ""
        ]

        self.__live_status.execute(";".join(query))
        log.debug("store ticket id (ec): %s", ";".join(query))

    def __render_comment(self):
        return "[Incident ID: %s]" % self.__id

    def __parse_comment(self, comment):
        match = re.search(r"\[Incident ID: ([^;\]]*)", comment)
        if match:
            return match.group(1)
        return None

    def close(self):
        if self.__source == Incident.Source.Notification:
            self.__remove_incident_id_notification()
        # no need to remove the incident id from the event console

    def identifier(self):
        return self.__id

    def set_identifier(self, identifier):
        self.__id = identifier
        if self.__source == Incident.Source.EventConsole:
            return self.__store_incident_id_ec()
        return self.__store_incident_id_notification()

    def event_type(self):
        return self.__type

    def what(self):
        return self.__what

    def host(self):
        return self.__host

    def service(self):
        return self.__service

    def message(self):
        return self.__message

    def state(self):
        return self.__state

    def time(self):
        return self.__time

    def contact(self):
        return self.__contact

    def service_level(self):
        return self.__service_level


#.
#   .--Message Renderer----------------------------------------------------.
#   |                __  __                                                |
#   |               |  \/  | ___  ___ ___  __ _  __ _  ___                 |
#   |               | |\/| |/ _ \/ __/ __|/ _` |/ _` |/ _ \                |
#   |               | |  | |  __/\__ \__ \ (_| | (_| |  __/                |
#   |               |_|  |_|\___||___/___/\__,_|\__, |\___|                |
#   |                                           |___/                      |
#   |              ____                _                                   |
#   |             |  _ \ ___ _ __   __| | ___ _ __ ___ _ __                |
#   |             | |_) / _ \ '_ \ / _` |/ _ \ '__/ _ \ '__|               |
#   |             |  _ <  __/ | | | (_| |  __/ | |  __/ |                  |
#   |             |_| \_\___|_| |_|\__,_|\___|_|  \___|_|                  |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Renderer(object):
    """
    Determines how the collected data from an incident is
    displayed to the user
    """
    def __init__(self, settings):
        super().__init__()

    @staticmethod
    def __render_state(state):
        return {
            "ok": "OK",
            "crit": "Critical",
            "warn": "Warning",
            "up": "Up",
            "down": "Down"
        }.get(state.lower(), state)

    def __render_time(self, event_time):
        return time.strftime("%Y-%m-%d %H:%M:%S", event_time)

    def render_title(self, incident):
        if incident.what() == Incident.What.Host:
            return "Host %(host)s is %(state)s!" % {
                'host': incident.host(),
                'state': self.__render_state(incident.state())
            }
        return "Service %(service)s on host %(host)s is %(state)s!" % {
            'service': incident.service(),
            'host': incident.host(),
            'state': self.__render_state(incident.state())
        }

    def render_message(self, incident):
        if incident.what() == Incident.What.Host:
            topic = "Host %(host)s is now in state %(state)s" % {
                'host': incident.host(),
                'state': self.__render_state(incident.state())
            }
            info = [("Time", self.__render_time(incident.time())),
                    ("Host output", incident.message())]
        else:
            topic = "Service %(service)s on host %(host)s is now in state %(state)s" % {
                'service': incident.service(),
                'host': incident.host(),
                'state': incident.state()
            }
            info = [("Time", self.__render_time(incident.time())),
                    ("Service output", incident.message())]

        info_width = max([len(key) for key, value in info])

        return "%s\n\n%s" % (topic, "\n".join(
            ["%s: %s" % (key.ljust(info_width), value) for key, value in info]))


#.
#   .--LiveStatus----------------------------------------------------------.
#   |           _     _           ____  _        _                         |
#   |          | |   (_)_   _____/ ___|| |_ __ _| |_ _   _ ___             |
#   |          | |   | \ \ / / _ \___ \| __/ _` | __| | | / __|            |
#   |          | |___| |\ V /  __/___) | || (_| | |_| |_| \__ \            |
#   |          |_____|_| \_/ \___|____/ \__\__,_|\__|\__,_|___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class LiveStatus(object):
    def __init__(self, socket_path):
        self.__livestatus_path = socket_path

    def query(self, lql):
        sock = socket(AF_UNIX, SOCK_STREAM)
        sock.connect(self.__livestatus_path)

        sock.send(lql + "\n")
        sock.shutdown(SHUT_WR)

        for line in sock.makefile():
            yield line

    def query_obj(self, lql):
        lql = lql + "\nOutputFormat: python\n"
        obj_string = "\n".join(list(self.query(lql)))
        return ast.literal_eval(obj_string) if obj_string else []

    def execute(self, lql):
        sock = socket(AF_UNIX, SOCK_STREAM)
        sock.connect(self.__livestatus_path)

        sock.send(lql + "\n")
        sock.close()


#.
#   .--Ticket Interface----------------------------------------------------.
#   |                      _____ _      _        _                         |
#   |                     |_   _(_) ___| | _____| |_                       |
#   |                       | | | |/ __| |/ / _ \ __|                      |
#   |                       | | | | (__|   <  __/ |_                       |
#   |                       |_| |_|\___|_|\_\___|\__|                      |
#   |                                                                      |
#   |              ___       _             __                              |
#   |             |_ _|_ __ | |_ ___ _ __ / _| __ _  ___ ___               |
#   |              | || '_ \| __/ _ \ '__| |_ / _` |/ __/ _ \              |
#   |              | || | | | ||  __/ |  |  _| (_| | (_|  __/              |
#   |             |___|_| |_|\__\___|_|  |_|  \__,_|\___\___|              |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class TicketInterface(object):
    """
    Base class for interfaces to the ticket system
    """
    interfaces = {}

    class Urgency(object):
        Low, Medium, High, Ultra = range(4)

    def __init__(self, settings):
        super().__init__()

    def register_arguments(self, opt):
        pass

    def login(self):
        return True

    def logout(self):
        return True

    def create_ticket(self, title, message, urgency, ticket_id):
        """
        create a ticket in the ticket system. parameters should be obvious
        ticket_id is a generated identifier from the monitoring system.
        The ticket system needs to store it somehow and be able to lookup
        tickets by this id.
        """
        raise NotImplementedError("create_ticket not implemented")

    def add_ticket_comment(self, ticket_id, message):
        raise NotImplementedError("add_ticket_comment not implemented")

    def close_ticket(self, ticket_id, message):
        raise NotImplementedError("close_ticket not implemented")

    @staticmethod
    def register(name, interface_class):
        TicketInterface.interfaces[name] = interface_class

    @staticmethod
    def instantiate(name, settings):
        return TicketInterface.interfaces[name](settings)


#.
#   .--GLPI----------------------------------------------------------------.
#   |                         ____ _     ____ ___                          |
#   |                        / ___| |   |  _ \_ _|                         |
#   |                       | |  _| |   | |_) | |                          |
#   |                       | |_| | |___|  __/| |                          |
#   |                        \____|_____|_|  |___|                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class InterfaceGLPI(TicketInterface):

    from xmlrpc.client import Error, Fault, ProtocolError, ResponseError, ServerProxy  # nosec

    urgency_map = {
        TicketInterface.Urgency.Low: 1,
        TicketInterface.Urgency.Medium: 3,
        TicketInterface.Urgency.High: 5,
        TicketInterface.Urgency.Ultra: 6
    }

    def __init__(self, settings):
        super().__init__(settings)
        self.__username = settings['username']
        self.__password = settings['password']
        self.__server = InterfaceGLPI.ServerProxy("http://%(host)s:%(port)s/%(url)s" % settings)
        self.__session = None
        # is the name returned by doLogin the same as the login_name? I presume not,
        # otherwise what would be the point of returning it?
        self.__own_name = None

    def login(self):
        try:
            response = self.__server.glpi.doLogin({
                'login_name': self.__username,
                'login_password': self.__password
            })
        except InterfaceGLPI.Fault as f:
            log.error("GLPI fault code %s, details: %s", f.faultCode, f.faultString)
            raise
        except InterfaceGLPI.ResponseError:
            # response error seems to hold no data?
            log.exception("response error on login. Is host and port configured correctly?")
            raise
        except InterfaceGLPI.ProtocolError as e:
            log.error("protocol error %s on login. Headers: %s", e.errcode, e.headers)
            raise

        if 'session' in response and 'name' in response:
            self.__session = response['session']
            self.__own_name = response['name']
        else:
            raise Exception("failed to login to server. Response was: %s" % response)

    def logout(self):
        if self.__session:
            self.__server.glpi.doLogout({'session': self.__session})

    def create_ticket(self, title, message, urgency, ticket_id):
        # typo in glpi webservices api: "urgancy"
        response = self.__server.glpi.createTicket({
            'session': self.__session,
            'title': title,
            'content': message,
            'urgancy': InterfaceGLPI.urgency_map[urgency],
        })
        log.debug("create ticket response: %s", response)
        return response['id']

    # def __resolve_id(self, ticket_id):
    #     response = self.__server.listTickets({
    #         'recipient': self.__own_name,    # only tickets reported through this account
    #         'status': 'notclosed'
    #     })

    #     for ticket in response:
    #         # title and name of a ticket are the same thing, the naming is not consistent
    #         # in the API
    #         if ticket['name'].endswith(self.__format_ticket_id(ticket_id)):
    #             return ticket['id']

    def add_ticket_comment(self, ticket_id, message):
        log.info("sess %s, tick %s, cont %s", self.__session, ticket_id, message)
        self.__server.glpi.addTicketFollowup({
            'session': self.__session,
            'ticket': ticket_id,
            'content': message
        })

    def close_ticket(self, ticket_id, message):
        response = self.__server.glpi.setTicketSolution({
            'session': self.__session,
            'ticket': ticket_id,
            'type': 1,
            'solution': message
        })
        log.debug("set solution response: %s", response)


TicketInterface.register("glpi", InterfaceGLPI)

#.
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def import_settings(base_dir):
    ticket_cfg = os.path.join(base_dir, "etc", "tickets.cfg")
    defaults_cfg = os.path.join(base_dir, "etc", "check_mk", "defaults")

    settings = {
        'product': os.path.splitext(os.path.basename(__file__))[0],
        'port': 80,
        'url': "",
        'prio_high_sl': 30,
        'prio_low_sl': 10,
    }

    if os.path.isfile(defaults_cfg):
        exec(open(defaults_cfg).read(), settings, settings)
    if os.path.isfile(ticket_cfg):
        exec(open(ticket_cfg).read(), settings, settings)

    # execfile put all tho globals into settings, including modules.
    # This doesn't acually hurt but let's clean up a bit anyway
    return {
        key: value  #
        for key, value in settings.items()
        if isinstance(value, (bool, int, str))
    }


def init_logging(base_dir, settings):
    log_path = os.path.join(base_dir, "var", "log", "ticket.log")

    base_handler = logging.FileHandler(log_path)
    formatter = logging.Formatter('%(asctime)s %(message)s')
    base_handler.setFormatter(formatter)
    log.addHandler(base_handler)

    log_level = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARN,
        "warning": logging.WARNING,
        "error": logging.ERROR
    }.get(settings.get("log_level"), logging.INFO)

    log.setLevel(log_level)


def handle_problem(renderer, ticket_interface, settings, incident):
    def determine_urgency(settings, incident):
        if incident.service_level() >= settings['prio_high_sl']:
            urgency = TicketInterface.Urgency.High
        elif incident.service_level() <= settings['prio_low_sl']:
            urgency = TicketInterface.Urgency.Low
        else:
            urgency = TicketInterface.Urgency.Medium
        if incident.state() == "CRITICAL":
            urgency += 1
        return urgency

    title = renderer.render_title(incident)
    message = renderer.render_message(incident)
    if incident.identifier() is None:
        urgency = determine_urgency(settings, incident)
        log.info("Creating ticket: title=%s, urgency=%s", title, urgency)
        ticket_id = ticket_interface.create_ticket(title, message, urgency)
        incident.set_identifier(ticket_id)
    else:
        log.info("Adding to ticket %s", incident.identifier())
        ticket_interface.add_ticket_comment(incident.identifier(), message)


def handle_recovery(renderer, ticket_interface, settings, incident):
    message = renderer.render_message(incident)

    if incident.identifier() is None:
        log.error(
            "Failed to close ticket regarding host \"%s\", service \"%s\" as the "
            "ticket id was not found in comments. "
            "Message would have been: \"%s\"", incident.host(), incident.service(), message)
    else:
        log.info("Closing ticket %s", incident.identifier())
        ticket_interface.close_ticket(incident.identifier(), message)
        incident.close()


def main():
    base_dir = os.environ['OMD_ROOT']
    settings = import_settings(base_dir)

    init_logging(base_dir, settings)

    # Initialize incident
    if "EC_ID" in os.environ:
        ec_socket_path = os.path.join(base_dir, "tmp", "run", "mkeventd", "status")
        live_status = LiveStatus(ec_socket_path)
        incident = Incident.from_event_console(os.environ, live_status)
    else:
        live_status = LiveStatus(settings['livestatus_unix_socket'])
        incident = Incident.from_notification(os.environ, live_status)

    if incident.identifier():
        log.info("incident has an id: %s", incident.identifier())

    handlers = {
        Incident.Type.Problem: handle_problem,
        Incident.Type.Recovery: handle_recovery,
    }

    # handle the incident, if there is a handler for it
    if incident.event_type() in handlers.keys():
        renderer = Renderer(settings)
        ticket_interface = TicketInterface.instantiate(settings['product'], settings)
        ticket_interface.login()
        handlers[incident.event_type()](renderer, ticket_interface, settings, incident)
        ticket_interface.logout()  # nop if there was no login
    else:
        log.info("Not handling event type %s", incident.event_type())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        if log is not None:
            log.exception("Unhandled exception")
        else:
            logging.exception("Unhandled exception")

#.
