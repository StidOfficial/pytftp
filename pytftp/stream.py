import io

class Stream(io.BytesIO):
  def __init__(self, bytes: bytes = b""):
    super().__init__(bytes)
  
  def read_uint8(self):
    return int.from_bytes(self.read(1), "big", signed = False)

  def write_uint8(self, value: int):
    self.write(value.to_bytes(1, "big", signed = False))

  def read_uint16(self):
    return int.from_bytes(self.read(2), "big", signed = False)

  def write_uint16(self, value: int):
    self.write(value.to_bytes(2, "big", signed = False))

  def read_uint32(self):
    return int.from_bytes(self.read(4), "big", signed = False)

  def write_uint32(self, value: int):
    self.write(value.to_bytes(4, "big", signed = False))

  def read_string(self):
    str = ""

    while True:
      byte = self.read(1)
      if len(byte) == 0 or byte == b"\x00":
        break

      str += byte.decode()

    return str

  def write_string(self, value: str):
    if value == None:
      self.write(b"\x00")
    else:
      self.write(value.encode() + b"\x00")