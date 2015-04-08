#!/usr/bin/env python2.7

from __future__ import unicode_literals
from argparse import ArgumentParser
from sys import stdout
from re import compile

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from txzmq import ZmqEndpoint, ZmqFactory, ZmqSubConnection, ZmqEndpointType
from twisted.python import log
from twisted.internet import reactor
import requests


_errorTemplate = '{"error":{"id":%i,"message":"%s"}}'


class PushjetProtocol(WebSocketServerProtocol):
    uuidRe = compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')

    def __init__(self):
        self.zmq = None
        self.uuid = None
        self.subscriptions = []

    @staticmethod
    def isUuid(s):
        return bool(PushjetProtocol.uuidRe.match(s))

    def onConnect(self, request):
        print "New connection:", request.peer

    def onMessage(self, payload, isBinary):
        if isBinary:
            message = _errorTemplate % (-1, 'Expected text got binary data')
            self.sendClose(None, message)
        elif self.uuid:  # Already initialized
            return
        elif not PushjetProtocol.isUuid(payload):
            message = _errorTemplate % (1, 'Invalid client uuid')
            self.sendClose(None, message)
        else:  # Initialize ZMQ
            self.uuid = payload

            self.zmq = ZmqSubConnection(zmqFactory, zmqEndpoint)
            self.zmq.gotMessage = self.onZmqMessage
            self.updateSubscriptionsAsync()

            self.sendMessage("{'status': 'ok'}")

    def onZmqMessage(self, message, tag):
        self.sendMessage(message)

        if tag == self.uuid:
            self.updateSubscriptionsAsync()

    def markReadAsync(self):
        self.factory.reactor.callFromThread(self.markRead)

    def markRead(self):
        url = "%s/message?uuid=%s" % (args.api.rstrip('/'), self.uuid)
        data = requests.delete(url).json()

        if 'error' in data:
            print "Could mark messages read for %s got error %i: %s" % (
                self.uuid, data['error']['id'], data['error']['message']
            )

    def updateSubscriptionsAsync(self):
        self.factory.reactor.callFromThread(self.updateSubscriptions)

    def updateSubscriptions(self):
        url = "%s/listen?uuid=%s" % (args.api.rstrip('/'), self.uuid)
        listens = requests.get(url).json()

        if 'error' in listens:
            print "Could not fetch listens for %s got error %i: %s" % (
                self.uuid, listens['error']['id'], listens['error']['message']
            )
        else:
            tokens = [x['service']['public'] for x in listens['listen']]

            # Make sure we are always listening to messages that are meant
            # for our client
            tokens.append(self.uuid)

            unsubscribe = [x for x in self.subscriptions if x not in tokens]
            subscribe = [x for x in tokens if x not in self.subscriptions]
            self.subscriptions = tokens

            map(self.zmq.unsubscribe, unsubscribe)
            map(self.zmq.subscribe, subscribe)
            print "Successfully updated listens for %s" % self.uuid


if __name__ == '__main__':
    parser = ArgumentParser(description='Pushjet websocket server')

    parser.add_argument('--host', '-u', default='127.0.0.1', type=str,
                        help='the host the server should bind to (default: 127.0.0.1, this is sane)')
    parser.add_argument('--port', '-p', default='8181', type=int,
                        help='the port the server should bind to (default: 8181)')
    parser.add_argument('--api', '-a', default='https://api.pushjet.io', type=str, metavar='SRV',
                        help='the api server url (default: https://api.pushjet.io)')
    parser.add_argument('--pub', '-z', default='ipc:///tmp/pushjet-publisher.ipc', type=str,
                        help='the publisher uri for receiving messages (default: ipc:///tmp/pushjet-publisher.ipc)')
    parser.add_argument('--log', '-l', default=None, type=str, metavar='PATH', dest='logfile',
                        help='log file path')
    parser.add_argument('--quiet', '-q', action='store_true')

    args = parser.parse_args()

    if not args.quiet:
        log.startLogging(stdout)
    if args.logfile:
        log.startLogging(open(args.logfile, 'a'))
        print("Started logging to file %s" % args.logfile)

    wsUri = 'ws://%s:%i' % (args.host, args.port)

    factory = WebSocketServerFactory(wsUri, debug=False)
    factory.protocol = PushjetProtocol

    zmqFactory = ZmqFactory()
    zmqEndpoint = ZmqEndpoint(ZmqEndpointType.connect, args.pub)

    reactor.listenTCP(args.port, factory)
    reactor.run()