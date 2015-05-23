from re import compile
from txzmq import ZmqEndpoint, ZmqFactory, ZmqSubConnection, ZmqEndpointType
import json
import requests


_zmqFactory = ZmqFactory()


class PushjetProtocolBase(object):
    _uuidRe = compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
    _errorTemplate = '{"error":{"id":%i,"message":"%s"}}'

    def __init__(self, apiUri, pubUri):
        self.api = apiUri.rstrip('/')
        self.zmqEndpoint = ZmqEndpoint(ZmqEndpointType.connect, pubUri)
        self.zmq = None
        self.uuid = None
        self.subscriptions = []

    @staticmethod
    def isUuid(s):
        return bool(PushjetProtocolBase._uuidRe.match(s))

    def onZmqMessage(self, data):
        tag, message = data.split(' ', 1)
        self.sendMessage(message)

        decoded = json.loads(message)
        if 'message' in decoded:
            self.markReadAsync()
        if 'listen' in decoded:
            token = decoded['listen']['service']['public']
            if token in self.subscriptions:
                self.zmq.unsubscribe(token)
            else:
                self.zmq.subscribe(token)

    def markReadAsync(self):
        self.factory.reactor.callFromThread(self.markRead)

    def markRead(self):
        url = "%s/message?uuid=%s" % (self.api, self.uuid)
        data = requests.delete(url).json()

        if 'error' in data:
            print "Could mark messages read for %s got error %i: %s" % (
                self.uuid, data['error']['id'], data['error']['message']
            )

    def getMessages(self):
        url = "%s/message?uuid=%s" % (self.api, self.uuid)
        data = requests.get(url).json()

        if 'error' in data:
            print "Could fetch messages for %s got error %i: %s" % (
                self.uuid, data['error']['id'], data['error']['message']
            )
            return []
        return data['messages']

    def updateSubscriptionsAsync(self):
        self.factory.reactor.callFromThread(self.updateSubscriptions)

    def updateSubscriptions(self):
        url = "%s/listen?uuid=%s" % (self.api, self.uuid)
        listens = requests.get(url).json()

        if 'error' in listens:
            print "Could not fetch listens for %s got error %i: %s" % (
                self.uuid, listens['error']['id'], listens['error']['message']
            )
        else:
            tokens = [x['service']['public'] for x in listens['listens']]

            # Make sure we are always listening to messages that are meant
            # for our client
            tokens.append(self.uuid)

            unsubscribe = [self.toAscii(x) for x in self.subscriptions if x not in tokens]
            subscribe   = [self.toAscii(x) for x in tokens if x not in self.subscriptions]
            self.subscriptions = tokens

            map(self.zmq.unsubscribe, unsubscribe)
            map(self.zmq.subscribe, subscribe)
            print "Successfully updated listens for %s" % self.uuid

    def onClientMessage(self, payload, binary=False):
        if binary:
            message = self._errorTemplate % (-1, 'Expected text got binary data')
            self.sendMessage(message)
        elif self.uuid:  # Already initialized
            return
        elif not self.isUuid(payload):
            message = self._errorTemplate % (1, 'Invalid client uuid')
            self.sendMessage(message)
        else:  # Initialize ZMQ
            self.uuid = payload

            self.zmq = ZmqSubConnection(_zmqFactory, self.zmqEndpoint)
            self.zmq.gotMessage = self.onZmqMessage
            self.updateSubscriptionsAsync()

            self.sendMessage("{'status': 'ok'}")

            msg = self.getMessages()
            for m in msg:
                self.sendMessage(json.dumps({'message': m}))

    @staticmethod
    def toAscii(s):
        return s.encode('ascii', 'ignore')

    def sendMessage(self, message):
        raise NotImplementedError()
