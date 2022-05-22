import enum

class Error(enum.Enum):
  EUNDEF = 0
  ENOTFOUND = 1
  EACCESS = 2
  ENOSPACE = 3
  EBADOP = 4
  EBADID = 5
  EEXISTS = 6
  ENOUSER = 7
  EOPTNEG = 8

  def get_message(self) -> str:
    return [
      "Not defined, see error message (if any).",
      "File not found.",
      "Access violation.",
      "Disk full or allocation exceeded.",
      "Illegal TFTP operation.",
      "Unknown transfer ID.",
      "File already exists.",
      "No such user.",
      "Failed to negotiate options"
    ][self.value]