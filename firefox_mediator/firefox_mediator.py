#!/usr/bin/env python

import json
import logging
import struct
import sys

FORMAT = '%(asctime)-15s %(levelname)-10s %(message)s'
logging.basicConfig(
    format=FORMAT,
    filename='/tmp/firefox_mediator.log',
    level=logging.DEBUG)
_logger = logging.getLogger('firefox_mediator')

# try:

# Python 3.x version
# Read a message from stdin and decode it.


def getMessage():
    rawLength = sys.stdin.buffer.read(4)
    if len(rawLength) == 0:
        sys.exit(0)
    messageLength = struct.unpack('@I', rawLength)[0]
    message = sys.stdin.buffer.read(messageLength).decode('utf-8')
    return json.loads(message)

# Encode a message for transmission,
# given its content.


def encodeMessage(messageContent):
    encodedContent = json.dumps(messageContent).encode('utf-8')
    encodedLength = struct.pack('@I', len(encodedContent))
    return {'length': encodedLength, 'content': encodedContent}

# Send an encoded message to stdout


def sendMessage(encodedMessage):
    sys.stdout.buffer.write(encodedMessage['length'])
    sys.stdout.buffer.write(encodedMessage['content'])
    sys.stdout.buffer.flush()


_logger.info('Starting mediator...')
while True:
    receivedMessage = getMessage()
    _logger.info('Received: %s', receivedMessage)
    if receivedMessage == "ping":
        sendMessage(encodeMessage("pong3"))
_logger.info('Exiting mediator...')

# except AttributeError:
#     # Python 2.x version (if sys.stdin.buffer is not defined)
#     # Read a message from stdin and decode it.
#     def getMessage():
#         rawLength = sys.stdin.read(4)
#         if len(rawLength) == 0:
#             sys.exit(0)
#         messageLength = struct.unpack('@I', rawLength)[0]
#         message = sys.stdin.read(messageLength)
#         return json.loads(message)

#     # Encode a message for transmission,
#     # given its content.
#     def encodeMessage(messageContent):
#         encodedContent = json.dumps(messageContent)
#         encodedLength = struct.pack('@I', len(encodedContent))
#         return {'length': encodedLength, 'content': encodedContent}

#     # Send an encoded message to stdout
#     def sendMessage(encodedMessage):
#         sys.stdout.write(encodedMessage['length'])
#         sys.stdout.write(encodedMessage['content'])
#         sys.stdout.flush()

#     while True:
#         receivedMessage = getMessage()
#         if receivedMessage == "ping":
#             sendMessage(encodeMessage("pong2"))
