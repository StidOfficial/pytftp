import os
from pytftp.server import Server

TFTPD_ADDR = os.getenv("TFTPD_ADDR", "")
TFTPD_PORT = os.getenv("TFTPD_PORT", 69)
TFTPD_BASE = os.getenv("TFTPD_BASE", "/var/lib/tftp")
TFTPD_BLKSIZE = os.getenv("TFTPD_BLKSIZE", Server.DEFAULT_BLKSIZE)
TFTPD_TIMEOUT = os.getenv("TFTPD_TIMEOUT", Server.DEFAULT_TIMEOUT)

tftpd = Server((TFTPD_ADDR, TFTPD_PORT), TFTPD_BASE, TFTPD_BLKSIZE, TFTPD_TIMEOUT)

print("Listen...")

try:
  tftpd.listen()
except KeyboardInterrupt:
  pass