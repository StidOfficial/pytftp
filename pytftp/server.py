import socket
import os.path
from pytftp.exception import TftpException
from pytftp.packet import Packet
from pytftp.opcode import Opcode
from pytftp.error import Error
from pytftp.file_mode import FileMode
from pytftp.access_mode import AccessMode
from pytftp.utils import Utils

class Client:
  def __init__(self, address: tuple, file_path: str,
                access_mode: AccessMode, mode: FileMode, options: dict,
                blksize: int, timeout: int, windowsize: int):
    self.__address = address
    self.__file = open(file_path, self.get_access_mode(mode, access_mode))
    self.__access_mode = access_mode
    self.__block = 0
    self.__end = False
    self.__shutdown = False
    self.__options = options
    self.__blksize = blksize
    self.__timeout = timeout
    self.__windowsize = windowsize

    file_size = os.path.getsize(file_path)

    if "blksize" in self.__options:
      client_blksize = int(self.__options["blksize"])
      
      if client_blksize <= self.__blksize:
        self.__options["blksize"] = client_blksize
        self.__blksize = client_blksize
    else:
      self.__blksize = Packet.MAX_SIZE

    if "tsize" in self.__options:
      self.__options["tsize"] = file_size

    if "timeout" in self.__options:
      client_timeout = int(self.__options["timeout"])

      if client_timeout <= self.__timeout:
        self.__options["timeout"] = client_timeout
        self.__timeout = client_timeout

    if "windowsize" in self.__options:
      self.__windowsize = int(self.__options["windowsize"])

    self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.__socket.settimeout(self.__timeout)

  def get_access_mode(self, mode: FileMode, access_mode: AccessMode) -> str:
    str_mode = ""

    if access_mode == AccessMode.READ:
      str_mode += "rb"
    elif access_mode == AccessMode.WRITE:
      str_mode += "wb"

    return str_mode

  def send_packet(self, packet: Packet):
    self.__socket.sendto(packet.getvalue(), self.__address)

  def send_block(self, resend = False):
    real_block_size = self.__blksize - 2 + 2

    if resend:
      self.__file.seek(real_block_size * self.__block)

    for block in range(self.__block, self.__block + self.__windowsize):
      packet = Packet()
      packet.write_opcode(Opcode.DATA)
      packet.write_uint16(block % (0xffff + 1))

      buffer = self.__file.read(real_block_size)
      packet.write(buffer)

      self.send_packet(packet)

      if len(buffer) < real_block_size:
        self.__end = True
        break

  def send_oack(self):
    packet = Packet()
    packet.write_opcode(Opcode.OACK)
    packet.write_options(self.__options)

    self.send_packet(packet)

  def send_ack(self):
    packet = Packet()
    packet.write_opcode(Opcode.ACK)
    packet.write_uint16(self.__block)

    self.send_packet(packet)

  def send_error(self, error: Error):
    packet = Packet()
    packet.write_opcode(Opcode.ERROR)
    packet.write_error(error)
    packet.write_string(error.get_message())

    self.send_packet(packet)

    self.__shutdown = True

  def ack_file(self, block: int):
    current_block = self.__block % 0xffff

    if block != 0 and block < current_block:
      print(Utils.addr_to_str(self.__address), f"block {block} is already validated")
      return

    self.__block += (block - current_block) + 1
    self.send_block()

  def listen(self):
    if len(self.__options.keys()) > 0:
      self.send_oack()
    else:
      self.__block = 1
      self.send_block()

    retry = 0

    while not self.__shutdown:
      try:
        data, addr = self.__socket.recvfrom(Packet.MAX_SIZE, socket.MSG_DONTWAIT)

        if len(data) < 3:
          print(Utils.addr_to_str(self.__address), "invalid packet size")
          continue

        retry = 0

        packet = Packet(data)

        opcode = packet.read_opcode()
        if opcode == Opcode.RRQ or opcode == Opcode.WRQ:
          print(Utils.addr_to_str(self.__address), "read or write already requested")

          self.send_error(Error.EBADOP)
        elif opcode == Opcode.DATA:
          block = packet.read_uint16()
          data = packet.read()

          if self.__access_mode == AccessMode.READ:
            print(Utils.addr_to_str(self.__address), "cannot read in write mode")
            raise TftpException(Error.EBADOP)

          print(Utils.addr_to_str(self.__address), block, data)
        elif opcode == Opcode.ACK:
          block = packet.read_uint16()

          if self.__end:
            break

          self.ack_file(block)
        elif opcode == Opcode.ERROR:
          error_code = packet.read_error()
          error_msg = packet.read_string()

          print(Utils.addr_to_str(self.__address), error_code, error_msg)

          break
        else:
          print(Utils.addr_to_str(self.__address), f"invalid packet {opcode}")

          continue
      except TimeoutError:
        if retry == 5:
          print(Utils.addr_to_str(self.__address), f"lost connection")
          break

        print(Utils.addr_to_str(self.__address), f"timeout, retry")

        self.send_block(resend = True)

        retry += 1
      except TftpException as e:
        print(Utils.addr_to_str(addr), e.error)

        self.send_error(addr, e.error)

    self.__file.close()

class Server:
  DEFAULT_BLKSIZE = 8192
  DEFAULT_TIMEOUT = 4
  DEFAULT_WINDOWSIZE = 1

  def __init__(self, address: tuple, base: str, blksize: int = DEFAULT_BLKSIZE,
                timeout: int = DEFAULT_TIMEOUT, windowsize: int = DEFAULT_WINDOWSIZE):
    self.__base = os.path.abspath(base)
    self.__blksize = blksize
    self.__timeout = timeout
    self.__windowsize = windowsize

    self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.__socket.bind(address)

  def send_packet(self, address: tuple, packet: Packet):
    self.__socket.sendto(packet.getvalue(), address)

  def send_error(self, address: tuple, error: Error):
    packet = Packet()
    packet.write_opcode(Opcode.ERROR)
    packet.write_error(error)
    packet.write_string(error.get_message())

    self.send_packet(address, packet)

  def get_file_name(self, file_path) -> str:
    return file_path.replace(f"{self.__base}/", "")

  def open_file(self, address: tuple, filename: str, mode: FileMode,
                access_mode: AccessMode, options: dict):
    # Patch Windows separator
    filename = filename.replace("\\", os.path.sep)

    file_path = os.path.normpath(f"{self.__base}/{filename}")

    if not file_path.startswith(self.__base):
      raise TftpException(Error.EACCESS)
    
    print(Utils.addr_to_str(address), access_mode, self.get_file_name(file_path), mode,
          options)

    try:
      client = Client(address, file_path, access_mode, mode, options,
                      self.__blksize, self.__timeout, self.__windowsize)
      client.listen()
    except FileNotFoundError:
      print(Utils.addr_to_str(address), file_path, "file not found")

      raise TftpException(Error.ENOTFOUND)

  def listen(self):
    while True:
      data, addr = self.__socket.recvfrom(Packet.MAX_SIZE)

      if len(data) < 3:
        print(Utils.addr_to_str(addr), "invalid packet size")
        continue

      try:
        packet = Packet(data)

        opcode = packet.read_opcode()
        if opcode == Opcode.RRQ:
          filename = packet.read_string()
          mode = FileMode(packet.read_string())
          options = packet.read_options()

          self.open_file(addr, filename, mode, AccessMode.READ, options)
        elif opcode == Opcode.WRQ:
          filename = packet.read_string()
          mode = FileMode(packet.read_string())
          options = packet.read_options()

          self.open_file(addr, filename, mode, AccessMode.READ, options)
        elif opcode == Opcode.DATA or opcode == Opcode.ACK or \
              opcode == Opcode.ACK or opcode == Opcode.OACK:
          print(Utils.addr_to_str(addr), f"cannot do {opcode}")
          self.send_error(addr, Error.EBADOP)
        else:
          print(Utils.addr_to_str(addr), f"invalid packet {opcode}")
      except TftpException as e:
        print(Utils.addr_to_str(addr), e.error)

        self.send_error(addr, e.error)