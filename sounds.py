import pygame
import math
import struct
import random

def _mk_sound(freq=800, ms=80, vol=0.5, decay=35):
    try:
        sr = 44100
        n = int(sr * ms / 1000)
        buf = b''
        rng = random.Random(42)
        for i in range(n):
            t = i / sr
            env = math.exp(-decay * t) * vol
            ns = rng.uniform(-0.12, 0.12)
            v = env * (0.5*math.sin(2*math.pi*freq*t) +
                       0.25*math.sin(2*math.pi*freq*1.47*t) +
                       0.15*math.sin(2*math.pi*freq*2.09*t) + 0.1*ns)
            buf += struct.pack('<h', max(-32767, min(32767, int(v*32767))))
        return pygame.mixer.Sound(buffer=buf)
    except Exception:
        return type('DummySound', (), {'play': lambda self: None})()

SND_MOVE = _mk_sound(700, 55, 0.35, 45)
SND_CAP = _mk_sound(350, 120, 0.55, 20)
SND_CHECK = _mk_sound(900, 90, 0.4, 35)
SND_ILLEGAL = _mk_sound(180, 130, 0.2, 18)
