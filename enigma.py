from collections import deque 
from configparser import ConfigParser
from consts import ALPHABET_SIZE, ALPHABET_UNIVERSE, NUM_ROTORS
from json import dumps, loads
from random import randint, shuffle

# Helper functions
def randomNumber():
  return randint(0, ALPHABET_SIZE)

def charToNumber(char):
  return ord(char) - ord('a')

def numberToChar(number):
  return chr(ord('a') + number)

def getRandomPlugboardString():
  keys = []
  numPairs = randint(1, 10)
  mapping = deque([x for x in ALPHABET_UNIVERSE])
  for _ in range(numPairs):
    shuffle(mapping)
    numA, numB = mapping.popleft(), mapping.popleft()
    keys.append("{}{}".format(numberToChar(numA), numberToChar(numB)))
  return " ".join(keys)

class AlphabetRing:
  def __init__(self):
    self.__notch = randomNumber() # initial distance away from pawl
  
  def loadCfg(self, cfg, cfgSection):
    self.__notch = int(cfg[cfgSection]["notch"])

  def saveCfg(self, cfg, cfgSection):
    if cfgSection not in cfg.sections():
      cfg[cfgSection] = {}
    cfg[cfgSection]["notch"] = str(self.__notch)
  
  @property
  def notch(self):
    return self.__notch

# Non-configurable
class RotorDisc:
  def __init__(self):
    self.__mapping = deque([x for x in ALPHABET_UNIVERSE])
    shuffle(self.__mapping)

  def get(self, num):
    assert(num in ALPHABET_UNIVERSE)
    return self.__mapping[num]

  def loadCfg(self, cfg, cfgSection):
    self.__mapping = deque(loads(cfg[cfgSection]["config"]))

  def saveCfg(self, cfg, cfgSection):
    if cfgSection not in cfg.sections():
      cfg[cfgSection] = {}
    cfg[cfgSection]["config"] = dumps(list(self.__mapping))

  def rotate(self):
    self.__mapping.rotate(1)

# Configurable. 
# The difference between a rotor disc and a reflector is its configurability.
# Also, a reflector is at the end of the 
class Reflector:
  def __init__(self):
    self.__mapping = [x for x in ALPHABET_UNIVERSE]
    shuffle(self.__mapping)
  
  def get(self, num):
    assert(num in ALPHABET_UNIVERSE)
    return self.__mapping[num]

  def loadCfg(self, cfg, cfgSection = "Reflector"):
    self.__mapping = loads(cfg[cfgSection]["config"])

  def saveCfg(self, cfg, cfgSection = "Reflector"):
    if cfgSection not in cfg.sections():
      cfg[cfgSection] = {}
    cfg[cfgSection]["config"] = dumps(self.__mapping)

class Plugboard:
  def __init__(self):
    self.__mapping = [x for x in ALPHABET_UNIVERSE]
    self.__str     = getRandomPlugboardString()
    self.__setup()
  
  def __setup(self):
    for keys in self.__str.split(" "):
      keys = keys.lower()
      self.__connect(keys[0], keys[1])
  
  def __connect(self, keyA, keyB):
    assert(keyA != keyB)
    numA = charToNumber(keyA)
    numB = charToNumber(keyB)
    assert(numA in ALPHABET_UNIVERSE)
    assert(numB in ALPHABET_UNIVERSE)
    self.__mapping[numA] = numB
    self.__mapping[numB] = numA

  def get(self, num):
    return self.__mapping[num]

  def loadCfg(self, cfg, cfgSection = "Plugboard"):
    self.__str = cfg[cfgSection]["settings"]
    self.__setup()

  def saveCfg(self, cfg, cfgSection = "Plugboard"):
    if cfgSection not in cfg.sections():
      cfg[cfgSection] = {}
    cfg[cfgSection]["settings"] = self.__str

# Rotor consists of RotorDisc and AlphabetRing
class Rotor:
  def __init__(self, ringstellung = randomNumber()):
    self._rotor_disc    = RotorDisc()
    self._alphabet_ring = AlphabetRing()
 
    # Wikipedia: There was the ability to adjust the alphabet ring relative to the rotor disc. 
    # The position of the ring was known as the Ringstellung ("ring setting"), and that 
    # setting was a part of the initial setup needed prior to an operating session.
    # The above information can be modeled using a random relative shift.
    self.__ringstellung = ringstellung

  def rotate(self):
    self._rotor_disc.rotate()

  @property
  def alphabet_ring(self):
    return self._alphabet_ring

  def loadCfg(self, cfg, cfgSection):
    self.__ringstellung = int(cfg[cfgSection]['Ringstellung'])
    self._rotor_disc.loadCfg(cfg, cfgSection)
    self._alphabet_ring.loadCfg(cfg, cfgSection)

  def saveCfg(self, cfg, cfgSection):
    if cfgSection not in cfg.sections():
      cfg[cfgSection] = {}
    cfg[cfgSection]['Ringstellung'] = str(self.__ringstellung)
    self._rotor_disc.saveCfg(cfg, cfgSection)
    self._alphabet_ring.saveCfg(cfg, cfgSection)

  def get(self, num):
    num = (num + self.__ringstellung) % ALPHABET_SIZE
    return self._rotor_disc.get(num)

# This is used for mechanically rotating the rotors
class PawlAndRatchetMechanism:
  def __init__(self, rotors):
    self._rotors         = rotors
    self._n              = len(rotors)
    self._rotation_count = [0 for _ in range(self._n - 1)]

  def __rotate_rotor(self, index):
      self._rotation_count[index] = (self._rotation_count[index] + 1) % ALPHABET_SIZE
      self._rotors[index].rotate()

  def rotate(self):
    pending_rotations = [False for _ in range(len(self._rotors))]
    # The first motor always rotates.
    pending_rotations[0] = True
    # Other rotors      
    for idx in range(1, self._n):
      if (self._rotation_count[idx-1] == self._rotors[idx-1].alphabet_ring.notch):
        pending_rotations[idx] = True

    # Perform the pending rotations
    for idx, pending in enumerate(pending_rotations):
      if pending:
        self.__rotate_rotor(idx)
      
# RotorAssembly consists of 3-4 rotors arranged linearly with a reflector at the end of it.
# The rotorAssembly is also mounted on top of a acuator bar which has a pawl-and-ratchet mechanism
# which helps to turn the rotors mechanically.
class RotorAssembly:
  def __init__(self):
    self._rotors    = [Rotor() for _ in range(0, NUM_ROTORS)]
    self._reflector = Reflector()
    self._prm       = PawlAndRatchetMechanism(self._rotors)

  def rotate(self):
    self._prm.rotate()

  def get(self, num):
    # The current (a light in the form of current) passed through the rotors 1-2-3, 
    # the reflector and then again through rotors 3-2-1
    obj_list = self._rotors + [self._reflector] + self._rotors[::-1]
    def apply(value, idx):
      if idx == len(obj_list):
        return value
      else:
        return apply(obj_list[idx].get(value), idx+1)

    value = apply(num, 0)
    # Rotate using PawlAndRatchetMechanism
    self._prm.rotate()

    return value

  def loadCfg(self, cfg):
    if "Reflector" in cfg.sections():
      self._reflector.loadCfg(cfg)
    
    for idx, rotor in enumerate(self._rotors):
      rotorSectionName = "Rotor_{0}".format(idx+1)
      rotor.loadCfg(cfg, rotorSectionName)

  def saveCfg(self, cfg):
    self._reflector.saveCfg(cfg, "Reflector")
    for idx, rotor in enumerate(self._rotors):
      rotorSectionName = "Rotor_{0}".format(idx+1)
      rotor.saveCfg(cfg, rotorSectionName)    

class Keyboard:
  @staticmethod
  def pressKey(key):
    key = key.lower()
    value = charToNumber(key)
    assert(value in ALPHABET_UNIVERSE)
    return value

class LightingBox:
  @staticmethod
  def lightUp(num):
    char = numberToChar(num)
    print(char)
    return char

class Enigma:
  def __init__(self):
    self._rotor_asm = RotorAssembly()
    self._plugboard = Plugboard()
    self._config    = ConfigParser()

  @staticmethod
  def isConfigFilePresent(configFilePath):
    from pathlib import Path
    return Path(configFilePath).is_file()

  # Load the given config. Needed for decryption
  def loadCfg(self, configFilePath):
    if Enigma.isConfigFilePresent(configFilePath):
      self._config.read(configFilePath)
      self._rotor_asm.loadCfg(self._config)
  
  # Save the initial config. Essential for decryption
  def saveCfg(self, configFilePath):
    self._rotor_asm.saveCfg(self._config)
    self._plugboard.saveCfg(self._config)
    with open(configFilePath, "w") as configFile:
      self._config.write(configFile)

  def get(self, num):
    num = self._plugboard.get(num)
    num = self._rotor_asm.get(num)
    num = self._plugboard.get(num)
    return num

  def run(self):
    while True:
      key = input()
      num = self.get(Keyboard.pressKey(key))
      LightingBox.lightUp(num)
