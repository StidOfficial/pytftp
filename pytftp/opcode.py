import enum

class Opcode(enum.Enum):
        RRQ = 1
        WRQ = 2
        DATA = 3
        ACK = 4
        ERROR = 5
        OACK = 6