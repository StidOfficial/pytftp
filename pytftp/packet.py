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

  def read_options(self) -> dict:
    options = {}

    while True:
      option = self.read_string()
      value = self.read_string()

      if len(option) == 0:
        break

      options[option] = value

    return options

  def write_options(self, value: dict):
    for key, value in value.items():
        self.write_string(key)
        self.write_string(str(value))