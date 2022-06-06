from pytftp.error import Error

class TftpException(Exception):
  def __init__(self, error: Error):
    super().__init__(error.get_message())

    self.error = error