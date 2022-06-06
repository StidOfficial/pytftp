#!/usr/bin/python3
import os
from pytftp.server import Server

TFTPD_ADDR = os.getenv("TFTPD_ADDR", "")
TFTPD_PORT = os.getenv("TFTPD_PORT", 69)
TFTPD_BASE = os.getenv("TFTPD_BASE", "/var/lib/tftp")
TFTPD_BLKSIZE = os.getenv("TFTPD_BLKSIZE", Server.DEFAULT_BLKSIZE)
TFTPD_TIMEOUT = os.getenv("TFTPD_TIMEOUT", Server.DEFAULT_TIMEOUT)
TFTPD_WINDOWSIZE = os.getenv("TFTPD_WINDOWSIZE", Server.DEFAULT_WINDOWSIZE)

tftpd = Server((TFTPD_ADDR, TFTPD_PORT), TFTPD_BASE, TFTPD_BLKSIZE, TFTPD_TIMEOUT, \
                TFTPD_WINDOWSIZE)

print("Listen...")

try:
  tftpd.listen()
except KeyboardInterrupt:
  pass