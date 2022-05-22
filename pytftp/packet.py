from pytftp.stream import Stream
from pytftp.opcode import Opcode
from pytftp.error import Error

class Packet(Stream):
  MAX_SIZE = 512

  def __init__(self, bytes = b""):
    super().__init__(bytes)

  def read_opcode(self) -> Opcode:
    return Opcode(self.read_uint16())

  def write_opcode(self, opcode: Opcode):
    self.write_uint16(opcode.value)

  def read_error(self) -> Error:
    return Error(self.read_uint16())

  def write_error(self, error: Error):
    self.write_uint16(error.value)