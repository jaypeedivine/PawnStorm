import os
import sys
import pygame

os.environ.setdefault('SDL_ANDROID_TRAP_BACK_BUTTON', '1')

import chess

if getattr(sys, 'frozen', False):
    _BASE = sys._MEIPASS
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(_BASE, 'fonts')

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

class L:
    _di = pygame.display.Info()
    _max = min(_di.current_w - 320, _di.current_h - 160)
    SQ = max(52, min(88, _max // 8))
    BOARD_PX = SQ * 8
    EVAL_W = 26
    PANEL_W = 235
    TOP_H = 50
    BOT_H = 52
    WIN_W = EVAL_W + BOARD_PX + PANEL_W
    WIN_H = TOP_H + BOARD_PX + BOT_H
    BX = EVAL_W

def _font(name, size, bold=False):
    if name == 'mono':
        return pygame.font.Font(os.path.join(FONT_DIR, 'mono.ttf'), size)
    path = os.path.join(FONT_DIR, 'bold.ttf' if bold else 'regular.ttf')
    return pygame.font.Font(path, size)

class F:
    _sc = 1.0
    FONT = _font('ui', 17)
    FONT_B = _font('ui', 17, True)
    FONT_SM = _font('ui', 13)
    FONT_XS = _font('ui', 11)
    FONT_LG = _font('ui', 36, True)
    FONT_TITLE = _font('ui', 48, True)
    FONT_MONO = _font('mono', 13)
    FONT_COACH = _font('ui', 15, True)

    @classmethod
    def rebuild(cls, sq):
        sc = max(0.55, sq / 72.0)
        if abs(sc - cls._sc) < 0.01:
            return
        cls._sc = sc
        cls.FONT = _font('ui', max(11, int(17 * sc)))
        cls.FONT_B = _font('ui', max(11, int(17 * sc)), True)
        cls.FONT_SM = _font('ui', max(9, int(13 * sc)))
        cls.FONT_XS = _font('ui', max(8, int(11 * sc)))
        cls.FONT_LG = _font('ui', max(18, int(36 * sc)), True)
        cls.FONT_TITLE = _font('ui', max(24, int(48 * sc)), True)
        cls.FONT_MONO = _font('mono', max(9, int(13 * sc)))
        cls.FONT_COACH = _font('ui', max(10, int(15 * sc)), True)

THEMES = {
    'Forest': ((235,236,208), (115,149,82)),
    'Walnut': ((240,217,181), (181,136,99)),
    'Ocean':  ((214,224,230), (120,150,170)),
    'Slate':  ((210,210,215), (130,130,150)),
}
THEME_NAMES = list(THEMES.keys())

C_WHITE = (255,255,255)
C_BG = (32,32,36)
C_PANEL = (38,38,42)
C_TOP = (44,44,48)
C_BTN = (60,120,170)
C_BTN_H = (80,145,200)
C_BTN_PLAY = (45,160,75)
C_BTN_PLAY_H = (55,185,90)
C_HL_YELLOW = (246,246,105,120)
C_HL_BLUE = (106,135,200,120)
C_PREMOVE = (150,80,200,100)
C_CHECK = (235,50,50,140)

COACH_COLORS = {
    'brilliant': (230,160,40), 'great': (100,180,80),
    'good': (160,200,160), 'ok': (180,180,180),
    'inaccuracy': (200,180,60), 'mistake': (220,130,50),
    'blunder': (210,50,50),
}
COACH_SYMBOLS = {
    'brilliant': '!!', 'great': '!', 'good': '', 'ok': '',
    'inaccuracy': '?!', 'mistake': '?', 'blunder': '??',
}
COACH_NAMES = {
    'brilliant': 'Brilliant!!', 'great': 'Great move!',
    'inaccuracy': 'Inaccuracy', 'mistake': 'Mistake',
    'blunder': 'Blunder!!',
}

TIME_CONTROLS = [
    ("Bullet 1+0", 60, 0), ("Bullet 2+1", 120, 1),
    ("Blitz 3+0", 180, 0), ("Blitz 3+2", 180, 2),
    ("Blitz 5+0", 300, 0), ("Blitz 5+3", 300, 3),
    ("Rapid 10+0", 600, 0), ("Rapid 15+10", 900, 10),
    ("Classical 30", 1800, 0), ("Zen", 0, 0),
]

AI_THINK_MIN = [0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
AI_THINK_JITTER = 0.4
COACH_MODES = ['Off', 'Live']

PIECE_VAL = {chess.PAWN:100, chess.KNIGHT:320, chess.BISHOP:330,
             chess.ROOK:500, chess.QUEEN:900, chess.KING:20000}

PST_PAWN = [
 0, 0, 0, 0, 0, 0, 0, 0,  5,10,10,-20,-20,10,10, 5,
 5,-5,-10, 0, 0,-10,-5, 5,  0, 0, 0,20,20, 0, 0, 0,
 5, 5,10,25,25,10, 5, 5, 10,10,20,30,30,20,10,10,
50,50,50,50,50,50,50,50,  0, 0, 0, 0, 0, 0, 0, 0]
PST_KNIGHT = [
-50,-40,-30,-30,-30,-30,-40,-50, -40,-20, 0, 0, 0, 0,-20,-40,
-30, 0,10,15,15,10, 0,-30, -30, 5,15,20,20,15, 5,-30,
-30, 0,15,20,20,15, 0,-30, -30, 5,10,15,15,10, 5,-30,
-40,-20, 0, 5, 5, 0,-20,-40, -50,-40,-30,-30,-30,-30,-40,-50]
PST_BISHOP = [
-20,-10,-10,-10,-10,-10,-10,-20, -10, 0, 0, 0, 0, 0, 0,-10,
-10, 0,10,10,10,10, 0,-10, -10, 5, 5,10,10, 5, 5,-10,
-10, 0, 5,10,10, 5, 0,-10, -10,10, 5,10,10, 5,10,-10,
-10, 5, 0, 0, 0, 0, 5,-10, -20,-10,-10,-10,-10,-10,-10,-20]
PST_ROOK = [
 0, 0, 0, 0, 0, 0, 0, 0,  5,10,10,10,10,10,10, 5,
-5, 0, 0, 0, 0, 0, 0,-5, -5, 0, 0, 0, 0, 0, 0,-5,
-5, 0, 0, 0, 0, 0, 0,-5, -5, 0, 0, 0, 0, 0, 0,-5,
-5, 0, 0, 0, 0, 0, 0,-5,  0, 0, 0, 5, 5, 0, 0, 0]
PST_QUEEN = [
-20,-10,-10,-5,-5,-10,-10,-20, -10, 0, 0, 0, 0, 0, 0,-10,
-10, 0, 5, 5, 5, 5, 0,-10,  -5, 0, 5, 5, 5, 5, 0,-5,
  0, 0, 5, 5, 5, 5, 0,-5, -10, 5, 5, 5, 5, 5, 0,-10,
-10, 0, 5, 0, 0, 0, 0,-10, -20,-10,-10,-5,-5,-10,-10,-20]
PST_KING = [
-30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30,
-30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30,
-20,-30,-30,-40,-40,-30,-30,-20, -10,-20,-20,-20,-20,-20,-20,-10,
 20, 20, 0, 0, 0, 0, 20, 20,  20, 30,10, 0, 0,10, 30, 20]

PST = {chess.PAWN:PST_PAWN, chess.KNIGHT:PST_KNIGHT, chess.BISHOP:PST_BISHOP,
       chess.ROOK:PST_ROOK, chess.QUEEN:PST_QUEEN, chess.KING:PST_KING}

OPENINGS = [
    ("e2e4 e7e5 g1f3 b8c6 f1b5", "Ruy Lopez"),
    ("e2e4 e7e5 g1f3 b8c6 f1c4", "Italian Game"),
    ("e2e4 e7e5 g1f3 b8c6 d2d4", "Scotch Game"),
    ("e2e4 e7e5 g1f3 g8f6", "Petrov Defense"),
    ("e2e4 e7e5 f2f4", "King's Gambit"),
    ("e2e4 c7c5", "Sicilian Defense"),
    ("e2e4 e7e6", "French Defense"),
    ("e2e4 c7c6", "Caro-Kann Defense"),
    ("e2e4 d7d5", "Scandinavian Defense"),
    ("e2e4 g8f6", "Alekhine Defense"),
    ("e2e4 d7d6", "Pirc Defense"),
    ("e2e4 g7g6", "Modern Defense"),
    ("d2d4 d7d5 c2c4 e7e6", "Queen's Gambit Declined"),
    ("d2d4 d7d5 c2c4 c7c6", "Slav Defense"),
    ("d2d4 d7d5 c2c4", "Queen's Gambit"),
    ("d2d4 g8f6 c2c4 g7g6", "King's Indian"),
    ("d2d4 g8f6 c2c4 e7e6", "Nimzo-Indian"),
    ("d2d4 g8f6 c2c4 c7c5", "Benoni Defense"),
    ("d2d4 f7f5", "Dutch Defense"),
    ("c2c4", "English Opening"),
    ("g1f3", "Reti Opening"),
    ("e2e4 e7e5 g1f3 b8c6", "Four Knights Setup"),
    ("e2e4 e7e5 g1f3", "King's Knight Opening"),
    ("e2e4 e7e5", "Open Game"),
    ("d2d4 d7d5", "Closed Game"),
    ("d2d4 g8f6 c2c4", "Indian Defense"),
    ("d2d4 g8f6", "Indian Game"),
    ("d2d4", "Queen's Pawn Game"),
    ("e2e4", "King's Pawn Game"),
]

def detect_opening(board):
    uci = " ".join(m.uci() for m in board.move_stack)
    best, best_len = "", 0
    for seq, name in OPENINGS:
        if uci.startswith(seq) and len(seq) > best_len:
            best, best_len = name, len(seq)
    return best or None
