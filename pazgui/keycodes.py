VLINE = 0x2502
ULCORNER = 0x250c
URCORNER = 0x2510
LLCORNER = 0x2514
LRCORNER = 0x2518
HLINE = 0x2500

SPACE = 0x20

def CTRL(key):
  key = key.upper()

  return chr(ord(key) - ord('A') + 1)

