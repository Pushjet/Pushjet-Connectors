#!/usr/bin/env python2

from argparse import ArgumentParser
from sys import stdout

from protocolBase import PushjetProtocolBase
from twisted.internet import reactor, protocol, endpoints
from twisted.protocols import basic
from twisted.python import log


class PushjetTCPBase(basic.LineOnlyReceiver, PushjetProtocolBase):
    magic_start = "\002"
    magic_end   = "\003"

    def __init__(self):
        PushjetProtocolBase.__init__(self, args.api, args.pub)
        self.onMessage = self.lineReceived
        self.lineReceived = self.onClientMessage

    def sendMessage(self, message):
        self.sendLine(self.magic_start + message + self.magic_end)


if __name__ == '__main__':
    parser = ArgumentParser(description='Pushjet websocket server')

    parser.add_argument('--port', '-p', default='7171', type=int,
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

    factory = protocol.Factory()
    factory.protocol = PushjetTCPBase

    endpoints.serverFromString(reactor, str("tcp:%i" % args.port)).listen(factory)
    reactor.run()
