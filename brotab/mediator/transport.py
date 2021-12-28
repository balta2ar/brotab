import json
import struct
import sys
from abc import ABC
from abc import abstractmethod
from typing import BinaryIO

from brotab.inout import TimeoutIO
from brotab.mediator.log import mediator_logger


class Transport(ABC):
    @abstractmethod
    def send(self, command: dict) -> None:
        pass

    @abstractmethod
    def recv(self) -> dict:
        pass


def default_transport() -> Transport:
    return StdTransport(sys.stdin.buffer, sys.stdout.buffer)


def transport_with_timeout(timeout: float) -> Transport:
    return StdTransport(TimeoutIO(sys.stdin.buffer, timeout),
                        TimeoutIO(sys.stdout.buffer, timeout))


class TransportError(Exception):
    pass


class StdTransport(Transport):
    def __init__(self, input_file: BinaryIO, output_file: BinaryIO):
        self._in = input_file
        self._out = output_file

    def reset(self):
        self._in.seek(0)
        self._out.seek(0)

    def send(self, command: dict) -> None:
        encoded = self._encode(command)
        mediator_logger.info('StdTransport SENDING: %s', command)
        self._out.write(encoded['length'])
        self._out.write(encoded['content'])
        self._out.flush()
        mediator_logger.info('StdTransport SENDING DONE: %s', command)

    def recv(self) -> dict:
        mediator_logger.info('StdTransport RECEIVING')
        raw_length = self._in.read(4)
        if len(raw_length) == 0:
            raise TransportError('StdTransport: cannot read, raw_length is empty')
        message_length = struct.unpack('@I', raw_length)[0]
        message = self._in.read(message_length).decode('utf8')
        mediator_logger.info('StdTransport RECEIVED: %s', message.encode('utf8'))
        return json.loads(message)

    def _encode(self, message):
        encoded_content = json.dumps(message).encode('utf8')
        encoded_length = struct.pack('@I', len(encoded_content))
        return {'length': encoded_length, 'content': encoded_content}
