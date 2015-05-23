#!/usr/bin/env python2.7

from __future__ import unicode_literals
from argparse import ArgumentParser
from sys import stdout

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from protocolBase import PushjetProtocolBase
from twisted.python import log
from twisted.internet import reactor


class PushjetWebSocketBase(WebSocketServerProtocol, PushjetProtocolBase):
    def __init__(self):
        PushjetProtocolBase.__init__(self, args.api, args.pub)
        WebSocketServerProtocol.__init__(self)
        self.onMessage = self.onClientMessage

    def onConnect(self, request):
        print "New connection:", request.peer

    def sendMessage(self, payload, **kwargs):
        return super(WebSocketServerProtocol, self).sendMessage(self.toAscii(payload), **kwargs)

    def closeConnection(self, message):
        self.sendMessage(message)
        return super(WebSocketServerProtocol, self)._closeConnection()


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
    factory.protocol = PushjetWebSocketBase

    reactor.listenTCP(args.port, factory)
    reactor.run()
