#!/usr/bin/env python2

from argparse import ArgumentParser
from sys import stdout

from protocolBase import PushjetProtocolBase
from twisted.internet import reactor, protocol
from twisted.python import log


class PushjetTCPBase(protocol.Protocol, PushjetProtocolBase):
    magic_start = '\002'
    magic_end   = '\003'
    uuid_len    = 36
    _buffer     = b''

    def __init__(self):
        PushjetProtocolBase.__init__(self, args.api, args.pub)

    def dataReceived(self, data):
        self._buffer += data
        if len(self._buffer) >= self.uuid_len:
            frame = self._buffer[:self.uuid_len]
            self._buffer = self._buffer[self.uuid_len:]
            print frame
            self.onClientMessage(frame)

    def sendMessage(self, message):
        self.transport.writeSequence((self.magic_start, message, self.magic_end))


class PushjetTCPBaseFactory(protocol.Factory):
    protocol = PushjetTCPBase

    def __init__(self, reactor):
        self.reactor = reactor

if __name__ == '__main__':
    parser = ArgumentParser(description='Pushjet websocket server')

    parser.add_argument('--port', '-p', default='7171', type=int,
                        help='the port the server should bind to (default: 7171)')
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

    reactor.listenTCP(args.port, PushjetTCPBaseFactory(reactor))
    reactor.run()
