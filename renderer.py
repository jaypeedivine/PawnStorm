import pygame
import chess
import math
import time
from config import (L, F, THEMES, C_WHITE, C_BG, C_PANEL, C_TOP,
                     C_BTN, C_BTN_H, C_BTN_PLAY, C_BTN_PLAY_H,
                     C_HL_YELLOW, C_HL_BLUE, C_PREMOVE, C_CHECK,
                     COACH_COLORS, COACH_SYMBOLS, COACH_NAMES,
                     THEME_NAMES, TIME_CONTROLS)
import pieces

def draw_eval_bar(game, screen):
    x, y, w, h = 0, L.TOP_H, L.EVAL_W, L.BOARD_PX
    pygame.draw.rect(screen, (30,30,30), (x, y, w, h))
    pct = game.coach.get_eval_pct()
    if game.flipped:
        pct = 1.0 - pct
    w_h = int(h * pct)
    b_h = h - w_h
    pygame.draw.rect(screen, (50,50,55), (x+1, y, w-2, b_h))
    pygame.draw.rect(screen, (220,220,215), (x+1, y+b_h, w-2, w_h))
    if game.coach.eval_history:
        ev = game.coach.eval_history[-1] / 100.0
        if abs(ev) > 90:
            s = "M" if ev > 0 else "-M"
        else:
            s = f"{ev:+.1f}"
        col = (30,30,30) if pct > 0.5 else (200,200,200)
        ey = max(y+1, min(y+h-14, y+b_h + (-12 if pct > 0.5 else 2)))
        t = F.FONT_XS.render(s, True, col)
        screen.blit(t, (x + (w - t.get_width())//2, ey))

def draw_board(game, screen):
    light, dark = THEMES[game.theme_name]
    for r in range(8):
        for c in range(8):
            col = light if (r+c)%2==0 else dark
            pygame.draw.rect(screen, col, (L.BX+c*L.SQ, L.TOP_H+r*L.SQ, L.SQ, L.SQ))
    for i in range(8):
        fc = i if not game.flipped else 7-i
        rc = 7-i if not game.flipped else i
        ft = F.FONT_XS.render('abcdefgh'[fc], True, dark if i%2==0 else light)
        screen.blit(ft, (L.BX+i*L.SQ+2, L.TOP_H+L.BOARD_PX-13))
        rt = F.FONT_XS.render('12345678'[rc], True, dark if i%2!=0 else light)
        screen.blit(rt, (L.BX+2, L.TOP_H+i*L.SQ+1))

def draw_highlights(game, screen):
    ov = pygame.Surface((L.SQ, L.SQ), pygame.SRCALPHA)
    if game.last_move:
        ov.fill(C_HL_YELLOW)
        for sq in [game.last_move.from_square, game.last_move.to_square]:
            screen.blit(ov, game.sq_to_px(sq))
    if game.selected is not None:
        ov.fill(C_HL_BLUE)
        screen.blit(ov, game.sq_to_px(game.selected))
    if game.board.is_check():
        ov.fill(C_CHECK)
        ksq = game.board.king(game.board.turn)
        if ksq is not None:
            screen.blit(ov, game.sq_to_px(ksq))
    for m in game.legal_for_selected:
        px, py = game.sq_to_px(m.to_square)
        dot = pygame.Surface((L.SQ, L.SQ), pygame.SRCALPHA)
        if game.board.piece_at(m.to_square):
            pygame.draw.circle(dot, (0,0,0,50), (L.SQ//2, L.SQ//2), L.SQ//2, 4)
        else:
            pygame.draw.circle(dot, (0,0,0,50), (L.SQ//2, L.SQ//2), L.SQ//8)
        screen.blit(dot, (px, py))
    if game.hint_move and game.hint_timer > 0:
        ho = pygame.Surface((L.SQ, L.SQ), pygame.SRCALPHA)
        ho.fill((50, 200, 50, 100))
        for sq in [game.hint_move.from_square, game.hint_move.to_square]:
            screen.blit(ho, game.sq_to_px(sq))
    if game.premove:
        po = pygame.Surface((L.SQ, L.SQ), pygame.SRCALPHA)
        po.fill(C_PREMOVE)
        for sq in game.premove:
            screen.blit(po, game.sq_to_px(sq))

def _draw_arrow(screen, game, from_sq, to_sq, color, alpha=120, width=None):
    fx, fy = game.sq_to_px(from_sq)
    tx, ty = game.sq_to_px(to_sq)
    fx += L.SQ // 2
    fy += L.SQ // 2
    tx += L.SQ // 2
    ty += L.SQ // 2
    w = width or max(4, L.SQ // 6)
    dx = tx - fx
    dy = ty - fy
    dist = max(1, math.sqrt(dx*dx + dy*dy))
    ux, uy = dx/dist, dy/dist
    px, py = -uy, ux
    head_len = min(w * 3, dist * 0.35)
    hx, hy = tx - ux * head_len, ty - uy * head_len
    shaft = [
        (fx + px*w*0.4, fy + py*w*0.4),
        (hx + px*w*0.4, hy + py*w*0.4),
        (hx + px*w, hy + py*w),
        (tx, ty),
        (hx - px*w, hy - py*w),
        (hx - px*w*0.4, hy - py*w*0.4),
        (fx - px*w*0.4, fy - py*w*0.4),
    ]
    surf = pygame.Surface((L.WIN_W, L.WIN_H), pygame.SRCALPHA)
    pygame.draw.polygon(surf, (*color, alpha), shaft)
    screen.blit(surf, (0, 0))

def draw_better_move_arrow(game, screen):
    if not game.coach.enabled or game.coach.feedback_timer <= 0:
        return
    last_half = len(game.board.move_stack) - 1
    if last_half < 1:
        return
    player_half = last_half - 1
    better = game.coach.better_moves.get(player_half)
    if not better:
        return
    better_move, better_san = better
    alpha = min(100, game.coach.feedback_timer * 2)
    _draw_arrow(screen, game, better_move.from_square, better_move.to_square,
                (80, 200, 120), alpha=alpha)

def draw_pieces(game, screen):
    anim_on = game.anim_piece is not None and (time.time() - game.anim_start) < game.anim_dur
    for sq in chess.SQUARES:
        if game.dragging and sq == game.drag_from:
            continue
        if anim_on and sq == game.anim_sq:
            continue
        pc = game.board.piece_at(sq)
        if pc:
            screen.blit(pieces.cache[(pc.piece_type, pc.color == chess.WHITE)], game.sq_to_px(sq))
    if anim_on:
        t = min(1.0, (time.time() - game.anim_start) / game.anim_dur)
        t = 1 - (1-t)**3
        ax = game.anim_from[0] + (game.anim_to[0]-game.anim_from[0])*t
        ay = game.anim_from[1] + (game.anim_to[1]-game.anim_from[1])*t
        screen.blit(pieces.cache[(game.anim_piece, game.anim_is_white)], (ax, ay))
    if game.dragging and game.drag_piece:
        s = pieces.cache[(game.drag_piece.piece_type, game.drag_piece.color == chess.WHITE)]
        screen.blit(s, s.get_rect(center=game.drag_pos))

def draw_thinking(game, screen):
    if not game.ai_thinking:
        return
    elapsed = time.time() - game.ai_think_start
    bar_h = 4
    bar_y = L.TOP_H + L.BOARD_PX - bar_h if not game.flipped else L.TOP_H
    phase = (math.sin(elapsed * 1.2) + 1) / 2
    glow_w = max(60, L.BOARD_PX // 3)
    cx = int(phase * L.BOARD_PX)
    base = pygame.Surface((L.BOARD_PX, bar_h), pygame.SRCALPHA)
    base.fill((235, 185, 60, 18))
    screen.blit(base, (L.BX, bar_y))
    widths = [glow_w, int(glow_w*0.65), int(glow_w*0.35), int(glow_w*0.15)]
    alphas = [25, 50, 100, 180]
    for w, a in zip(widths, alphas):
        s = pygame.Surface((max(1, w), bar_h), pygame.SRCALPHA)
        s.fill((255, 200, 75, a))
        screen.blit(s, (L.BX + cx - w // 2, bar_y))
    orb_r = max(3, L.SQ // 16)
    orb_alpha = int(100 + 60 * math.sin(elapsed * 2.5))
    orb_surf = pygame.Surface((orb_r*2, bar_h+orb_r*2), pygame.SRCALPHA)
    pygame.draw.circle(orb_surf, (255, 210, 90, orb_alpha), (orb_r, orb_r), orb_r)
    screen.blit(orb_surf, (L.BX + cx - orb_r, bar_y - orb_r + bar_h//2))

def draw_top_bar(game, screen):
    pygame.draw.rect(screen, C_TOP, (0, 0, L.WIN_W, L.TOP_H))
    def fmt(t):
        if t == float('inf'):
            return '\u221e'
        m, s = divmod(max(0, int(t)), 60)
        return f"{m}:{s:02d}"
    is_zen = game.white_time == float('inf')
    wact = game.board.turn == chess.WHITE and not game.game_over
    bact = game.board.turn == chess.BLACK and not game.game_over
    if not is_zen:
        screen.blit(F.FONT_B.render(f"W {fmt(game.white_time)}", True,
                     C_WHITE if wact else (140,140,140)), (10, 15))
        screen.blit(F.FONT_B.render(f"B {fmt(game.black_time)}", True,
                     C_WHITE if bact else (140,140,140)), (110, 15))
    else:
        screen.blit(F.FONT_SM.render("Zen Mode", True, (100,160,120)), (10, 18))
    if game.game_over:
        st = F.FONT_B.render(game.game_result, True, (255,220,50))
        screen.blit(st, (220, 15))
    elif game.ai_thinking:
        alpha_pulse = int(140 + 40 * math.sin(time.time() * 1.5))
        st = F.FONT.render("Pondering...", True, (alpha_pulse, alpha_pulse+20, alpha_pulse))
        screen.blit(st, (220, 16))
    elif game._is_player_turn():
        msg = "Your move" if is_zen else ("White to move" if game.board.turn == chess.WHITE else "Black to move")
        st = F.FONT.render(msg, True, (200,200,200))
        screen.blit(st, (220, 16))
    else:
        who = 'White' if game.board.turn == chess.WHITE else 'Black'
        st = F.FONT.render(f"{who} to move", True, (200,200,200))
        screen.blit(st, (220, 16))
    if game.opening_name:
        ot = F.FONT_SM.render(game.opening_name, True, (140,180,140))
        screen.blit(ot, (L.BX + L.BOARD_PX - ot.get_width() - 5, 2))
    if game.adaptive:
        lt = F.FONT_SM.render(f"Adaptive L{game.adaptive_level}", True, (180,220,180))
    else:
        lt = F.FONT_SM.render(f"Level {game.ai.level}", True, (160,180,200))
    screen.blit(lt, (L.BX + L.BOARD_PX - lt.get_width() - 5, L.TOP_H - 16))
    if game.coach.enabled:
        ct = F.FONT_XS.render("\u2691 Coach ON", True, (120,180,130))
        screen.blit(ct, (L.BX + 5, L.TOP_H - 14))
    yt = F.FONT_XS.render("You: " + ("White" if game.player_color == chess.WHITE else "Black"),
                            True, (120,120,120))
    screen.blit(yt, (L.BX + L.BOARD_PX + 10, 4))

def draw_bottom_bar(game, screen):
    bar_y = L.TOP_H + L.BOARD_PX
    pygame.draw.rect(screen, C_TOP, (0, bar_y, L.WIN_W, L.BOT_H))
    mx, my = pygame.mouse.get_pos()
    for rect, label in game.buttons:
        hover = rect.collidepoint(mx, my)
        pygame.draw.rect(screen, C_BTN_H if hover else C_BTN, rect, border_radius=5)
        t = F.FONT_SM.render(label, True, C_WHITE)
        screen.blit(t, t.get_rect(center=rect.center))

def draw_coach_feedback(game, screen):
    if not game.coach.enabled:
        return
    if not game.coach.last_feedback or game.coach.feedback_timer <= 0:
        return
    rating = game.coach.last_feedback
    txt = COACH_NAMES.get(rating)
    if not txt:
        return
    col = COACH_COLORS.get(rating, (180,180,180))
    alpha = min(220, game.coach.feedback_timer * 3)
    half = len(game.board.move_stack) - 2
    better = game.coach.better_moves.get(half)
    extra = f"  Better: {better[1]}" if better else ""
    full_txt = f"{COACH_SYMBOLS.get(rating, '')} {txt}{extra}"
    tw = max(200, F.FONT_COACH.size(full_txt)[0] + 24)
    s = pygame.Surface((tw, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, (*col[:3], min(200, alpha)), (0, 0, tw, 32), border_radius=8)
    ts = F.FONT_COACH.render(full_txt, True, C_WHITE)
    s.blit(ts, (tw//2 - ts.get_width()//2, 6))
    screen.blit(s, (L.BX + L.BOARD_PX//2 - tw//2, L.TOP_H + L.BOARD_PX - 42))

def draw_coach_tip(game, screen):
    if not game.coach.enabled or not game.coach.tip or game.coach.tip_timer <= 0:
        return
    if game.coach.feedback_timer > 0:
        return
    alpha = min(180, game.coach.tip_timer * 2)
    tip_txt = f"\u2691 {game.coach.tip}"
    tw = max(200, F.FONT_SM.size(tip_txt)[0] + 20)
    s = pygame.Surface((tw, 26), pygame.SRCALPHA)
    pygame.draw.rect(s, (60, 90, 70, min(180, alpha)), (0, 0, tw, 26), border_radius=6)
    ts = F.FONT_SM.render(tip_txt, True, (200, 230, 200))
    s.blit(ts, (tw//2 - ts.get_width()//2, 4))
    screen.blit(s, (L.BX + L.BOARD_PX//2 - tw//2, L.TOP_H + 8))

def _draw_panel_portrait(game, screen):
    py = L.TOP_H + L.BOARD_PX + L.BOT_H
    ph = max(0, L.WIN_H - py)
    if ph <= 0:
        return
    pygame.draw.rect(screen, C_PANEL, (0, py, L.WIN_W, ph))
    pygame.draw.line(screen, (60,60,60), (0, py), (L.WIN_W, py))
    SM = {'P': chess.PAWN, 'N': chess.KNIGHT, 'B': chess.BISHOP,
          'R': chess.ROOK, 'Q': chess.QUEEN, 'K': chess.KING}
    y = py + 4
    ix = 8
    you_w = game.player_color == chess.WHITE
    for label, caps, is_w in [
        ("You: " if you_w else "AI: ", game.captured_b, False),
        ("AI: " if you_w else "You: ", game.captured_w, True),
    ]:
        if caps:
            t = F.FONT_XS.render(label, True, (150,150,150))
            screen.blit(t, (ix, y))
            ix += t.get_width() + 2
            for sym in sorted(caps):
                pt = SM.get(sym)
                if pt:
                    icon = pieces.cache.get((pt, is_w, 'sm'))
                    if icon:
                        screen.blit(icon, (ix, y - 1))
                        ix += 18
            ix += 10
    y += 22
    if game.move_stack_san:
        mx = 8
        start = max(0, len(game.move_stack_san) - 20)
        start = start - (start % 2)
        for i in range(start, len(game.move_stack_san), 2):
            if y > py + ph - 14:
                break
            num = i // 2 + 1
            wm = game.move_stack_san[i]
            bm = game.move_stack_san[i+1] if i+1 < len(game.move_stack_san) else ""
            line = f"{num}.{wm} {bm}  "
            t = F.FONT_XS.render(line, True, (170,170,170))
            if mx + t.get_width() > L.WIN_W - 8:
                mx = 8
                y += 14
                if y > py + ph - 14:
                    break
            screen.blit(t, (mx, y))
            mx += t.get_width()

def draw_side_panel(game, screen):
    if game.portrait:
        _draw_panel_portrait(game, screen)
        return
    px = L.BX + L.BOARD_PX
    pygame.draw.rect(screen, C_PANEL, (px, 0, L.PANEL_W, L.WIN_H))
    pygame.draw.line(screen, (60,60,60), (px, 0), (px, L.WIN_H))
    y = L.TOP_H + 10
    screen.blit(F.FONT_B.render("Captured", True, (190,190,190)), (px+10, y))
    y += 22
    SM = {'P': chess.PAWN, 'N': chess.KNIGHT, 'B': chess.BISHOP,
          'R': chess.ROOK, 'Q': chess.QUEEN, 'K': chess.KING}
    def draw_caps(label, caps, is_w, yy):
        t = F.FONT_XS.render(label, True, (150,150,150))
        screen.blit(t, (px+10, yy))
        ix = px + 10 + t.get_width() + 3
        for sym in sorted(caps):
            pt = SM.get(sym)
            if pt:
                icon = pieces.cache.get((pt, is_w, 'sm'))
                if icon:
                    screen.blit(icon, (ix, yy-1))
                    ix += 20
    you_w = game.player_color == chess.WHITE
    if game.captured_b:
        draw_caps("You: " if you_w else "AI: ", game.captured_b, False, y)
    y += 20
    if game.captured_w:
        draw_caps("AI: " if you_w else "You: ", game.captured_w, True, y)
    y += 28
    if game.coach.enabled and game.coach.accuracy_scores:
        acc = game.coach.get_accuracy()
        acc_col = (100,200,100) if acc >= 70 else (220,180,60) if acc >= 40 else (210,80,80)
        screen.blit(F.FONT_SM.render(f"Accuracy: {acc:.0f}%", True, acc_col), (px+10, y))
        y += 18
    screen.blit(F.FONT_B.render("Moves", True, (190,190,190)), (px+10, y))
    y += 22
    start = game.scroll_offset * 2
    for i in range(start, len(game.move_stack_san), 2):
        if y > L.WIN_H - 30:
            break
        num = i // 2 + 1
        wm = game.move_stack_san[i]
        bm = game.move_stack_san[i+1] if i+1 < len(game.move_stack_san) else ""
        w_ann = game.coach.annotations.get(i, '')
        b_ann = game.coach.annotations.get(i+1, '')
        w_sym = COACH_SYMBOLS.get(w_ann, '')
        b_sym = COACH_SYMBOLS.get(b_ann, '')
        line = f"{num:2d}. {wm}{w_sym:3s} {bm}{b_sym}"
        col = (170,170,170)
        for ann in [w_ann, b_ann]:
            if ann == 'blunder': col = COACH_COLORS['blunder']; break
            if ann == 'mistake': col = COACH_COLORS['mistake']; break
            if ann == 'brilliant': col = COACH_COLORS['brilliant']; break
        screen.blit(F.FONT_MONO.render(line, True, col), (px+8, y))
        y += 16

def draw_promo_dialog(game, screen):
    ov = pygame.Surface((L.BOARD_PX, L.BOARD_PX), pygame.SRCALPHA)
    ov.fill((0,0,0,120))
    screen.blit(ov, (L.BX, L.TOP_H))
    cx = L.BX + L.BOARD_PX // 2
    cy = L.TOP_H + L.BOARD_PX // 2
    pygame.draw.rect(screen, (55,55,60), (cx-120, cy-35, 240, 70), border_radius=8)
    pygame.draw.rect(screen, (90,90,95), (cx-120, cy-35, 240, 70), 2, border_radius=8)
    is_w = game.player_color == chess.WHITE
    mx, my = pygame.mouse.get_pos()
    for i, pt in enumerate([chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]):
        r = pygame.Rect(cx - 100 + i*55, cy - 25, 48, 48)
        c = (80,80,85) if r.collidepoint(mx, my) else (65,65,70)
        pygame.draw.rect(screen, c, r, border_radius=4)
        icon = pieces.cache[(pt, is_w, 'md')]
        screen.blit(icon, icon.get_rect(center=r.center))

def draw_game_over(game, screen):
    if not game.game_over:
        return
    ov = pygame.Surface((L.BOARD_PX + L.EVAL_W, 100), pygame.SRCALPHA)
    ov.fill((0,0,0,190))
    cy = L.TOP_H + L.BOARD_PX//2
    screen.blit(ov, (0, cy - 50))
    gt = F.FONT_B.render(game.game_result, True, (255,220,50))
    screen.blit(gt, gt.get_rect(center=(L.BX+L.BOARD_PX//2, cy-20)))
    player_moves = [r for r in game.coach.annotations.values() if r]
    if player_moves and game.coach.enabled:
        bl = sum(1 for r in player_moves if r == 'blunder')
        ms = sum(1 for r in player_moves if r == 'mistake')
        br = sum(1 for r in player_moves if r == 'brilliant')
        gr = sum(1 for r in player_moves if r == 'great')
        acc = game.coach.get_accuracy()
        stats = f"Accuracy: {acc:.0f}%  |  !!:{br}  !:{gr}  ?:{ms}  ??:{bl}"
        st = F.FONT_XS.render(stats, True, (180,180,180))
        screen.blit(st, st.get_rect(center=(L.BX+L.BOARD_PX//2, cy)))
        review_txt = F.FONT_SM.render("[R] Review  |  [New] Play again", True, (160,200,160))
        screen.blit(review_txt, review_txt.get_rect(center=(L.BX+L.BOARD_PX//2, cy+18)))
    else:
        nt = F.FONT_SM.render("Press [New] to play again", True, (180,180,180))
        screen.blit(nt, nt.get_rect(center=(L.BX+L.BOARD_PX//2, cy+4)))
    if game.game_over and game.coach.enabled and game.move_stack_san:
        review_btn = pygame.Rect(L.BX + L.BOARD_PX//2 - 60, cy + 30, 120, 28)
        mx, my = pygame.mouse.get_pos()
        hover = review_btn.collidepoint(mx, my)
        pygame.draw.rect(screen, (70,140,90) if hover else (55,110,70), review_btn, border_radius=6)
        rt = F.FONT_SM.render("Review Game", True, C_WHITE)
        screen.blit(rt, rt.get_rect(center=review_btn.center))
        if not hasattr(game, '_review_btn'):
            game._review_btn = review_btn

def draw_review(game, screen):
    screen.fill(C_BG)
    tt = F.FONT_LG.render("Game Review", True, C_WHITE)
    screen.blit(tt, tt.get_rect(center=(L.WIN_W//2, 35)))
    acc = game.coach.get_accuracy()
    acc_col = (100,200,100) if acc >= 70 else (220,180,60) if acc >= 40 else (210,80,80)
    at = F.FONT_B.render(f"Accuracy: {acc:.0f}%", True, acc_col)
    screen.blit(at, at.get_rect(center=(L.WIN_W//2, 68)))
    annotations = game.coach.annotations
    counts = {}
    for v in annotations.values():
        counts[v] = counts.get(v, 0) + 1
    sx = L.WIN_W // 2 - 180
    sy = 90
    for rating in ['brilliant', 'great', 'good', 'ok', 'inaccuracy', 'mistake', 'blunder']:
        cnt = counts.get(rating, 0)
        if cnt == 0:
            continue
        col = COACH_COLORS.get(rating, (150,150,150))
        sym = COACH_SYMBOLS.get(rating, '')
        name = rating.capitalize()
        bar_w = min(200, cnt * 25)
        pygame.draw.rect(screen, (*col, 180), (sx, sy, bar_w, 16), border_radius=4)
        label = F.FONT_SM.render(f"{sym} {name}: {cnt}", True, C_WHITE)
        screen.blit(label, (sx + bar_w + 8, sy))
        sy += 22
    sy += 10
    review_data = game.coach.get_review_data(game.move_stack_san)
    header_y = sy
    hdr = F.FONT_B.render("  #   White          Black", True, (180,180,180))
    screen.blit(hdr, (sx - 10, header_y))
    sy += 22
    row_h = 20
    visible = min(len(review_data), max(5, (L.WIN_H - sy - 60) // row_h))
    start = game.review_scroll
    for idx in range(start, min(start + visible, len(review_data))):
        d = review_data[idx]
        num_txt = f"{d['num']:3d}."
        w_sym = COACH_SYMBOLS.get(d['w_ann'], '')
        b_sym = COACH_SYMBOLS.get(d['b_ann'], '')
        w_col = COACH_COLORS.get(d['w_ann'], (170,170,170))
        b_col = COACH_COLORS.get(d['b_ann'], (170,170,170))
        nt = F.FONT_MONO.render(num_txt, True, (120,120,120))
        screen.blit(nt, (sx - 10, sy))
        wt = F.FONT_MONO.render(f"{d['w_san']}{w_sym}", True, w_col)
        screen.blit(wt, (sx + 35, sy))
        if d['w_better']:
            bt = F.FONT_XS.render(f"\u2192{d['w_better']}", True, (100,180,100))
            screen.blit(bt, (sx + 35 + wt.get_width() + 4, sy + 2))
        if d['b_san']:
            bt2 = F.FONT_MONO.render(f"{d['b_san']}{b_sym}", True, b_col)
            screen.blit(bt2, (sx + 160, sy))
            if d['b_better']:
                bt3 = F.FONT_XS.render(f"\u2192{d['b_better']}", True, (100,180,100))
                screen.blit(bt3, (sx + 160 + bt2.get_width() + 4, sy + 2))
        sy += row_h
    if len(review_data) > visible:
        scroll_info = F.FONT_XS.render(f"Showing {start+1}-{min(start+visible, len(review_data))} of {len(review_data)}  (scroll to navigate)", True, (100,100,100))
        screen.blit(scroll_info, scroll_info.get_rect(center=(L.WIN_W//2, sy + 8)))
    btn_y = L.WIN_H - 50
    mx, my = pygame.mouse.get_pos()
    back_r = pygame.Rect(L.WIN_W//2 - 140, btn_y, 120, 34)
    game.review_back_rect = back_r
    hover = back_r.collidepoint(mx, my)
    pygame.draw.rect(screen, C_BTN_H if hover else C_BTN, back_r, border_radius=6)
    screen.blit(F.FONT_B.render("Back", True, C_WHITE), F.FONT_B.render("Back", True, C_WHITE).get_rect(center=back_r.center))
    new_r = pygame.Rect(L.WIN_W//2 + 20, btn_y, 120, 34)
    game.review_newgame_rect = new_r
    hover2 = new_r.collidepoint(mx, my)
    pygame.draw.rect(screen, C_BTN_PLAY_H if hover2 else C_BTN_PLAY, new_r, border_radius=6)
    screen.blit(F.FONT_B.render("New Game", True, C_WHITE), F.FONT_B.render("New Game", True, C_WHITE).get_rect(center=new_r.center))
    pygame.display.flip()

def draw_menu(game, screen):
    screen.fill(C_BG)
    tt = F.FONT_TITLE.render("PawnStorm", True, C_WHITE)
    screen.blit(tt, tt.get_rect(center=(L.WIN_W//2, 45)))
    sub = F.FONT_SM.render("Offline Chess \u2022 Play at your own pace", True, (120,120,125))
    screen.blit(sub, sub.get_rect(center=(L.WIN_W//2, 78)))
    mx, my = pygame.mouse.get_pos()
    game.menu_rects = []
    screen.blit(F.FONT_B.render("Difficulty", True, (200,200,200)), (L.WIN_W//2-150, 100))
    names = ['Beginner','Novice','Casual','Easy','Medium',
             'Intermediate','Strong','Advanced','Expert','Master']
    bw, bh, gap, cols = 135, 32, 5, 2
    sx = L.WIN_W//2 - (cols*bw + (cols-1)*gap)//2
    sy = 122
    for i in range(10):
        ri, ci = i // cols, i % cols
        rect = pygame.Rect(sx + ci*(bw+gap), sy + ri*(bh+gap), bw, bh)
        game.menu_rects.append((rect, i+1))
        hover = rect.collidepoint(mx, my)
        sel = not game.adaptive and game.menu_level == i+1
        col = (50,170,80) if sel else (C_BTN_H if hover else C_BTN)
        pygame.draw.rect(screen, col, rect, border_radius=5)
        t = F.FONT_SM.render(f"{i+1}. {names[i]}", True, C_WHITE)
        screen.blit(t, t.get_rect(center=rect.center))
    ay = sy + 5*(bh+gap) + 4
    ar = pygame.Rect(L.WIN_W//2-68, ay, 136, bh)
    game.adaptive_rect = ar
    acol = (180,120,50) if game.adaptive else (C_BTN_H if ar.collidepoint(mx,my) else C_BTN)
    pygame.draw.rect(screen, acol, ar, border_radius=5)
    at = F.FONT_B.render(f"Adaptive (L{game.adaptive_level})", True, C_WHITE)
    screen.blit(at, at.get_rect(center=ar.center))
    cy = ay + bh + 14
    screen.blit(F.FONT_B.render("Play as", True, (200,200,200)), (L.WIN_W//2-150, cy))
    cy += 20
    game.color_rects = []
    for i, (val, lbl) in enumerate([('white','White'),('black','Black'),('random','Random')]):
        cr = pygame.Rect(L.WIN_W//2-150+i*105, cy, 95, 28)
        game.color_rects.append((cr, val))
        sel = game.menu_color == val
        col = (50,170,80) if sel else (C_BTN_H if cr.collidepoint(mx,my) else C_BTN)
        pygame.draw.rect(screen, col, cr, border_radius=5)
        t = F.FONT_SM.render(lbl, True, C_WHITE)
        screen.blit(t, t.get_rect(center=cr.center))
    ty = cy + 38
    screen.blit(F.FONT_B.render("Time Control", True, (200,200,200)), (L.WIN_W//2-150, ty))
    ty += 20
    tcbw, tcbh, tcgap, tc_cols = 92, 25, 4, 4
    tc_sx = L.WIN_W//2 - (tc_cols*tcbw + (tc_cols-1)*tcgap)//2
    game.tc_rects = []
    for ti, (tname, _, _) in enumerate(TIME_CONTROLS):
        tr, tc = ti // tc_cols, ti % tc_cols
        tcr = pygame.Rect(tc_sx+tc*(tcbw+tcgap), ty+tr*(tcbh+tcgap), tcbw, tcbh)
        game.tc_rects.append((tcr, ti))
        sel = game.tc_idx == ti
        col = (50,170,80) if sel else (C_BTN_H if tcr.collidepoint(mx,my) else C_BTN)
        pygame.draw.rect(screen, col, tcr, border_radius=4)
        t = F.FONT_XS.render(tname, True, C_WHITE)
        screen.blit(t, t.get_rect(center=tcr.center))
    tc_rows = (len(TIME_CONTROLS) + tc_cols - 1) // tc_cols
    thy = ty + tc_rows*(tcbh+tcgap) + 8
    screen.blit(F.FONT.render("Theme:", True, (180,180,180)), (L.WIN_W//2-150, thy))
    game.theme_rects = []
    for i, tn in enumerate(THEME_NAMES):
        light, dark = THEMES[tn]
        tr = pygame.Rect(L.WIN_W//2-40+i*62, thy-2, 56, 22)
        game.theme_rects.append((tr, tn))
        sel = game.theme_name == tn
        bdr = (50,170,80) if sel else (70,70,70)
        pygame.draw.rect(screen, light, (tr.x, tr.y, 28, 22), border_radius=3)
        pygame.draw.rect(screen, dark, (tr.x+28, tr.y, 28, 22), border_radius=3)
        pygame.draw.rect(screen, bdr, tr, 2, border_radius=3)
    coy = thy + 30
    coach_r = pygame.Rect(L.WIN_W//2 - 80, coy, 160, 28)
    game.coach_rect = coach_r
    coach_on = game.menu_coach
    ccol = (60,140,80) if coach_on else (C_BTN_H if coach_r.collidepoint(mx,my) else (80,60,60))
    pygame.draw.rect(screen, ccol, coach_r, border_radius=5)
    clbl = "\u2691 Coach: ON" if coach_on else "\u2691 Coach: OFF"
    ct = F.FONT_B.render(clbl, True, C_WHITE)
    screen.blit(ct, ct.get_rect(center=coach_r.center))
    coach_desc = "Tips, move ratings, accuracy & game review" if coach_on else "Play without feedback"
    cd = F.FONT_XS.render(coach_desc, True, (120,120,120))
    screen.blit(cd, cd.get_rect(center=(L.WIN_W//2, coy + 36)))
    py = coy + 52
    pr = pygame.Rect(L.WIN_W//2-85, py, 170, 46)
    game.play_rect = pr
    pcol = C_BTN_PLAY_H if pr.collidepoint(mx,my) else C_BTN_PLAY
    pygame.draw.rect(screen, pcol, pr, border_radius=8)
    pt = F.FONT_LG.render("Play", True, C_WHITE)
    screen.blit(pt, pt.get_rect(center=pr.center))
    ft = F.FONT_XS.render("ESC = cancel premove | Drag & drop or click to move", True, (75,75,80))
    screen.blit(ft, ft.get_rect(center=(L.WIN_W//2, L.WIN_H-12)))
    pygame.display.flip()
