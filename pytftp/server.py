import socket
import time
import os.path
import math
from pytftp.exception import Exception
from pytftp.packet import Packet
from pytftp.opcode import Opcode
from pytftp.error import Error
from pytftp.file_mode import FileMode
from pytftp.access_mode import AccessMode

class Client:
  def __init__(self, address: tuple, file_path: str,
                access_mode: AccessMode, mode: FileMode, options: dict,
                blksize: int, timeout: int):
    self.__address = address
    self.__file = open(file_path, self.get_access_mode(mode, access_mode))
    self.__access_mode = access_mode
    self.__block = 0
    self.__end = False
    self.__options = options
    self.__blksize = blksize
    self.__timeout = timeout

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

    if file_size / self.__blksize > 65535:
      print(self.get_addr(), f"not enough available blocks with {self.__blksize} " \
            f"block size for {file_size} bytes, force with {blksize}")

      if "blksize" in self.__options:
        self.__options["blksize"] = blksize
      self.__blksize = blksize

    self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.__socket.settimeout(self.__timeout)

  def get_access_mode(self, mode: FileMode, access_mode: AccessMode) -> str:
    str_mode = ""

    if access_mode == AccessMode.READ:
      str_mode += "rb"
    elif access_mode == AccessMode.WRITE:
      str_mode += "wb"

    return str_mode

  def get_addr(self) -> str:
    return f"{self.__address[0]}:{self.__address[1]}"

  def send_packet(self, packet: Packet):
    self.__socket.sendto(packet.getvalue(), self.__address)

  def send_block(self, resend = False):
    real_block_size = self.__blksize - 2 + 2

    if not resend:
      self.__last_block = self.__file.read(real_block_size)

    packet = Packet()
    packet.write_opcode(Opcode.DATA)
    packet.write_uint16(self.__block)
    packet.write(self.__last_block)

    self.send_packet(packet)

    if len(self.__last_block) < real_block_size:
      self.__end = True

  def send_oack(self):
    packet = Packet()
    packet.write_opcode(Opcode.OACK)
    for key, value in self.__options.items():
      packet.write_string(key)
      packet.write_string(str(value))

    packet.write_string("")
    packet.write_string("")

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

  def ack_file(self, block: int):
    self.__block += 1
    self.send_block()

  def listen(self):
    if len(self.__options.keys()) > 0:
      self.send_oack()
    else:
      self.__block = 1
      self.send_block()

    retry = 0

    while True:
      try:
        data, addr = self.__socket.recvfrom(Packet.MAX_SIZE, socket.MSG_DONTWAIT)

        if len(data) < 3:
          print(self.get_addr(addr), "invalid packet size")
          continue

        retry = 0

        packet = Packet(data)

        opcode = packet.read_opcode()
        if opcode == Opcode.RRQ or opcode == Opcode.WRQ:
          self.send_error(Error.EBADOP)
        elif opcode == Opcode.DATA:
          block = packet.read_uint16()
          data = packet.read()

          file = self.get_file(addr)
          if file == None:
            raise Exception(Error.EBADOP)

          print(self.get_addr(), block, data)
        elif opcode == Opcode.ACK:
          block = packet.read_uint16()

          if self.__end:
            break

          self.ack_file(block)
        elif opcode == Opcode.ERROR:
          error_code = packet.read_error()
          error_msg = packet.read_string()

          print(self.get_addr(), error_code, error_msg)

          break
        else:
          print(self.get_addr(), f"invalid packet {opcode}")

          continue
      except TimeoutError:
        if retry == 5:
          break

        self.send_block(resend = True)

        retry += 1
      except Exception as ex:
        self.send_error(addr, ex.error)
        break

    self.__file.close()

class Server:
  DEFAULT_BLKSIZE = 8192
  DEFAULT_TIMEOUT = 4

  def __init__(self, address: tuple, base: str, blksize: int = DEFAULT_BLKSIZE,
                timeout: int = DEFAULT_TIMEOUT):
    self.__base = os.path.abspath(base)
    self.__blksize = blksize
    self.__timeout = timeout

    self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.__socket.bind(address)

  def get_addr(self, address: tuple) -> str:
    return f"{address[0]}:{address[1]}"

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

    file_path = os.path.normpath(os.path.join(self.__base, filename))

    if not file_path.startswith(self.__base):
      raise Exception(Error.EACCESS)
    
    print(self.get_addr(address), access_mode, self.get_file_name(file_path), mode,
          options)

    try:
      client = Client(address, file_path, access_mode, mode, options,
                      self.__blksize, self.__timeout)
      client.listen()
    except FileNotFoundError:
      raise Exception(Error.ENOTFOUND)

  def read_options(self, packet: Packet) -> dict:
    options = {}

    while True:
      option = packet.read_string()
      value = packet.read_string()

      if len(option) == 0:
        break

      options[option] = value

    return options

  def listen(self):
    while True:
      data, addr = self.__socket.recvfrom(Packet.MAX_SIZE)

      if len(data) < 3:
        print(self.get_addr(addr), "invalid packet size")
        continue

      try:
        packet = Packet(data)

        opcode = packet.read_opcode()
        if opcode == Opcode.RRQ:
          filename = packet.read_string()
          mode = FileMode(packet.read_string())
          options = self.read_options(packet)

          self.open_file(addr, filename, mode, AccessMode.READ, options)
        elif opcode == Opcode.WRQ:
          filename = packet.read_string()
          mode = FileMode(packet.read_string())
          options = self.read_options(packet)

          self.open_file(addr, filename, mode, AccessMode.READ, options)
        elif opcode == Opcode.DATA or opcode == Opcode.ACK or \
              opcode == Opcode.ACK or opcode == Opcode.OACK:
          self.send_error(addr, Error.EBADOP)
        else:
          print(self.get_addr(addr), f"invalid packet {opcode}")
      except Exception as ex:
        self.send_error(addr, ex.error)