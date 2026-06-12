import os
import sys
import pygame
import chess

if getattr(sys, 'frozen', False):
    FONT_DIR = os.path.join(sys._MEIPASS, 'fonts')
else:
    FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')

PIECE_CHARS = {
    (chess.KING, True): '\u2654', (chess.QUEEN, True): '\u2655',
    (chess.ROOK, True): '\u2656', (chess.BISHOP, True): '\u2657',
    (chess.KNIGHT, True): '\u2658', (chess.PAWN, True): '\u2659',
    (chess.KING, False): '\u265A', (chess.QUEEN, False): '\u265B',
    (chess.ROOK, False): '\u265C', (chess.BISHOP, False): '\u265D',
    (chess.KNIGHT, False): '\u265E', (chess.PAWN, False): '\u265F',
}

def _build(sz):
    c = {}
    pf = None
    for fname in ['symbols.ttf', 'dejavu.ttf']:
        try:
            f = pygame.font.Font(os.path.join(FONT_DIR, fname), int(sz * 0.82))
            if f.render('\u2654', True, (0,0,0)).get_width() > 5:
                pf = f
                break
        except Exception:
            continue
    if pf is None:
        pf = pygame.font.Font(None, int(sz * 0.82))
    for is_w in [True, False]:
        for pt in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]:
            ch = PIECE_CHARS[(pt, is_w)]
            surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
            out_c = (35,35,35) if is_w else (215,215,215)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx*dx + dy*dy <= 4:
                        t = pf.render(ch, True, out_c)
                        surf.blit(t, t.get_rect(center=(sz//2+dx, sz//2+dy)))
            fill_c = (255,248,235) if is_w else (40,40,40)
            t = pf.render(ch, True, fill_c)
            surf.blit(t, t.get_rect(center=(sz//2, sz//2)))
            c[(pt, is_w)] = surf
            c[(pt, is_w, 'sm')] = pygame.transform.smoothscale(surf, (22, 22))
            c[(pt, is_w, 'md')] = pygame.transform.smoothscale(surf, (40, 40))
    return c

from config import L
cache = _build(L.SQ)

def rebuild(sq):
    global cache
    cache = _build(sq)
