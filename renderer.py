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
    pct = game.coach.get_eval_pct()
    if game.flipped:
        pct = 1.0 - pct
    if L.IS_MOBILE:
        bar_h = 6
        bar_y = L.TOP_H - bar_h
        bar_x = L.BX
        bar_w = L.BOARD_PX
        pygame.draw.rect(screen, (30, 30, 30), (bar_x, bar_y, bar_w, bar_h))
        w_w = int(bar_w * pct)
        pygame.draw.rect(screen, (220, 220, 215), (bar_x, bar_y, w_w, bar_h))
        pygame.draw.rect(screen, (50, 50, 55), (bar_x + w_w, bar_y, bar_w - w_w, bar_h))
        if game.coach.eval_history:
            ev = game.coach.eval_history[-1] / 100.0
            if abs(ev) > 90:
                s = "M" if ev > 0 else "-M"
            else:
                s = f"{ev:+.1f}"
            col = (220, 220, 215) if pct > 0.5 else (150, 150, 155)
            t = F.FONT_XS.render(s, True, col)
            screen.blit(t, (bar_x + bar_w - t.get_width() - 4, bar_y - 13))
    else:
        x, y, w, h = 0, L.TOP_H, L.EVAL_W, L.BOARD_PX
        pygame.draw.rect(screen, (30,30,30), (x, y, w, h))
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
            return '--'
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
        ct = F.FONT_XS.render("Coach ON", True, (120,180,130))
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
    tip_txt = f"Tip: {game.coach.tip}"
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
    W, H = L.WIN_W, L.WIN_H
    screen.fill(C_BG)
    mx, my = pygame.mouse.get_pos()
    board = game.review_board

    # Board on the left
    bsz = min(L.SQ, (H - 100) // 8)
    board_px = bsz * 8
    bx, by = 10, 10
    light, dark = THEMES[game.theme_name]
    for r in range(8):
        for c in range(8):
            col = light if (r + c) % 2 == 0 else dark
            pygame.draw.rect(screen, col, (bx + c * bsz, by + r * bsz, bsz, bsz))
    for sq in chess.SQUARES:
        pc = board.piece_at(sq)
        if pc:
            file_idx = chess.square_file(sq)
            rank_idx = 7 - chess.square_rank(sq)
            img = pieces.cache.get((pc.piece_type, pc.color == chess.WHITE))
            if img:
                scaled = pygame.transform.smoothscale(img, (bsz, bsz))
                screen.blit(scaled, (bx + file_idx * bsz, by + rank_idx * bsz))

    # Highlight last move in review
    if game.review_idx > 0:
        last_mv = game.review_moves[game.review_idx - 1]
        ov = pygame.Surface((bsz, bsz), pygame.SRCALPHA)
        ov.fill(C_HL_YELLOW)
        for sq in [last_mv.from_square, last_mv.to_square]:
            fx = chess.square_file(sq)
            ry = 7 - chess.square_rank(sq)
            screen.blit(ov, (bx + fx * bsz, by + ry * bsz))
        # Show better move arrow
        half_idx = game.review_idx - 1
        better = game.coach.better_moves.get(half_idx)
        if better:
            bm = better[0]
            f_from = chess.square_file(bm.from_square)
            r_from = 7 - chess.square_rank(bm.from_square)
            f_to = chess.square_file(bm.to_square)
            r_to = 7 - chess.square_rank(bm.to_square)
            x1 = bx + f_from * bsz + bsz // 2
            y1 = by + r_from * bsz + bsz // 2
            x2 = bx + f_to * bsz + bsz // 2
            y2 = by + r_to * bsz + bsz // 2
            pygame.draw.line(screen, (80, 200, 120), (x1, y1), (x2, y2), 3)
            pygame.draw.circle(screen, (80, 200, 120), (x2, y2), 5)

    # Right panel
    px = bx + board_px + 12
    pw = W - px - 8
    py = 10

    # Accuracy header
    acc = game.coach.get_accuracy()
    acc_col = (100, 200, 100) if acc >= 70 else (220, 180, 60) if acc >= 40 else (210, 80, 80)
    screen.blit(F.FONT_B.render("Game Review", True, C_WHITE), (px, py))
    py += 20
    screen.blit(F.FONT_SM.render(f"Accuracy: {acc:.0f}%", True, acc_col), (px, py))
    py += 22

    # Move counter
    total = len(game.review_moves)
    pos_txt = f"Move {game.review_idx}/{total}"
    screen.blit(F.FONT_SM.render(pos_txt, True, (140, 140, 145)), (px, py))
    py += 24

    # Coach comment for current position
    comment, comment_col = game.get_review_comment()
    pygame.draw.rect(screen, (30, 30, 36), (px, py, pw, 48), border_radius=6)
    pygame.draw.rect(screen, (*comment_col, 180), (px, py, 4, 48), border_radius=2)
    lines = []
    if len(comment) > 40:
        mid = comment[:40].rfind(' ')
        if mid == -1:
            mid = 40
        lines = [comment[:mid], comment[mid:].strip()]
    else:
        lines = [comment]
    for li, line in enumerate(lines):
        ct = F.FONT_SM.render(line, True, comment_col)
        screen.blit(ct, (px + 10, py + 6 + li * 16))
    py += 58

    # Move list (clickable)
    screen.blit(F.FONT_B.render("Moves", True, (180, 180, 185)), (px, py))
    py += 20
    game.review_move_rects = []
    row_h = 16
    visible = max(5, (H - py - 60) // row_h)
    for i in range(0, len(game.move_stack_san), 2):
        if py > H - 70:
            break
        num = i // 2 + 1
        w_san = game.move_stack_san[i]
        b_san = game.move_stack_san[i + 1] if i + 1 < len(game.move_stack_san) else ""
        w_ann = game.coach.annotations.get(i, '')
        b_ann = game.coach.annotations.get(i + 1, '')
        w_col = COACH_COLORS.get(w_ann, (160, 160, 165))
        b_col = COACH_COLORS.get(b_ann, (160, 160, 165))
        w_sym = COACH_SYMBOLS.get(w_ann, '')
        b_sym = COACH_SYMBOLS.get(b_ann, '')
        # Highlight active move
        w_active = game.review_idx == i + 1
        b_active = game.review_idx == i + 2
        nt = F.FONT_XS.render(f"{num}.", True, (100, 100, 105))
        screen.blit(nt, (px, py))
        wr = pygame.Rect(px + 22, py - 1, 60, row_h)
        game.review_move_rects.append((wr, i + 1))
        if w_active:
            pygame.draw.rect(screen, (40, 80, 55), wr, border_radius=3)
        wt = F.FONT_XS.render(f"{w_san}{w_sym}", True, w_col)
        screen.blit(wt, (wr.x + 2, py))
        if b_san:
            br = pygame.Rect(px + 85, py - 1, 60, row_h)
            game.review_move_rects.append((br, i + 2))
            if b_active:
                pygame.draw.rect(screen, (40, 80, 55), br, border_radius=3)
            bt = F.FONT_XS.render(f"{b_san}{b_sym}", True, b_col)
            screen.blit(bt, (br.x + 2, py))
        py += row_h

    # Navigation buttons at bottom
    nav_y = H - 44
    nav_btns = [('|<', 'start'), ('<', 'back'), ('>', 'fwd'), ('>|', 'end')]
    game.review_nav = []
    btn_w = 44
    nav_x = bx + board_px // 2 - (btn_w * 4 + 12) // 2
    for i, (lbl, action) in enumerate(nav_btns):
        r = pygame.Rect(nav_x + i * (btn_w + 4), nav_y, btn_w, 34)
        game.review_nav.append((r, action))
        hover = r.collidepoint(mx, my)
        pygame.draw.rect(screen, C_BTN_H if hover else C_BTN, r, border_radius=6)
        t = F.FONT_B.render(lbl, True, C_WHITE)
        screen.blit(t, t.get_rect(center=r.center))

    # Exit / New Game buttons
    exit_r = pygame.Rect(W - 180, nav_y, 80, 34)
    game.review_nav.append((exit_r, 'exit'))
    hover_e = exit_r.collidepoint(mx, my)
    pygame.draw.rect(screen, C_BTN_H if hover_e else C_BTN, exit_r, border_radius=6)
    et = F.FONT_SM.render("Back", True, C_WHITE)
    screen.blit(et, et.get_rect(center=exit_r.center))

    new_r = pygame.Rect(W - 90, nav_y, 80, 34)
    game.review_nav.append((new_r, 'menu'))
    hover_n = new_r.collidepoint(mx, my)
    pygame.draw.rect(screen, C_BTN_PLAY_H if hover_n else C_BTN_PLAY, new_r, border_radius=6)
    nt2 = F.FONT_SM.render("New", True, C_WHITE)
    screen.blit(nt2, nt2.get_rect(center=new_r.center))

def _draw_card(screen, rect, hover=False, selected=False):
    if selected:
        pygame.draw.rect(screen, (38, 100, 55), rect, border_radius=8)
        pygame.draw.rect(screen, (81, 190, 95), rect, 2, border_radius=8)
    elif hover:
        pygame.draw.rect(screen, (48, 48, 55), rect, border_radius=8)
        pygame.draw.rect(screen, (70, 70, 78), rect, 1, border_radius=8)
    else:
        pygame.draw.rect(screen, (36, 36, 42), rect, border_radius=8)

def _star_points(cx, cy, outer, inner, points=5):
    pts = []
    for i in range(points * 2):
        angle = math.pi / 2 + i * math.pi / points
        r = outer if i % 2 == 0 else inner
        pts.append((cx + r * math.cos(angle), cy - r * math.sin(angle)))
    return pts

def _draw_mini_board(screen, x, y, size, light, dark, alpha=40):
    sq = size // 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    for r in range(4):
        for c in range(4):
            col = (*light, alpha) if (r + c) % 2 == 0 else (*dark, alpha)
            pygame.draw.rect(surf, col, (c * sq, r * sq, sq, sq))
    screen.blit(surf, (x, y))

def draw_menu(game, screen):
    W, H = L.WIN_W, L.WIN_H
    cx = W // 2
    mx, my = pygame.mouse.get_pos()

    screen.fill((18, 18, 22))

    # Subtle gradient overlay
    grad = pygame.Surface((W, H), pygame.SRCALPHA)
    for row in range(0, H, 2):
        a = max(0, 8 - int(8 * row / H))
        pygame.draw.line(grad, (81, 190, 95, a), (0, row), (W, row))
    screen.blit(grad, (0, 0))

    # Decorative mini boards in corners
    light, dark = THEMES[game.theme_name]
    _draw_mini_board(screen, -30, H - 140, 160, light, dark, 18)
    _draw_mini_board(screen, W - 100, -20, 120, light, dark, 12)

    # --- HEADER ---
    tt = F.FONT_TITLE.render("PawnStorm", True, (255, 255, 255))
    screen.blit(tt, tt.get_rect(center=(cx, 38)))
    sub = F.FONT_SM.render("Play chess offline against AI", True, (95, 100, 110))
    screen.blit(sub, sub.get_rect(center=(cx, 68)))

    # --- Scrollable single-column layout ---
    content_top = 90
    section_w = min(380, W - 40)
    sx = cx - section_w // 2
    y = content_top

    # === PLAY AS ===
    screen.blit(F.FONT_B.render("Play as", True, (200, 200, 205)), (sx, y))
    y += 24
    game.color_rects = []
    pw = (section_w - 16) // 3
    for i, (val, lbl) in enumerate([('white', 'White'), ('black', 'Black'), ('random', 'Random')]):
        cr = pygame.Rect(sx + i * (pw + 8), y, pw, 32)
        game.color_rects.append((cr, val))
        sel = game.menu_color == val
        hover = cr.collidepoint(mx, my)
        if sel:
            pygame.draw.rect(screen, (36, 110, 58), cr, border_radius=6)
            pygame.draw.rect(screen, (81, 190, 95), cr, 2, border_radius=6)
        elif hover:
            pygame.draw.rect(screen, (44, 44, 50), cr, border_radius=6)
        else:
            pygame.draw.rect(screen, (32, 32, 38), cr, border_radius=6)
        if val == 'white':
            pygame.draw.circle(screen, (220, 220, 215) if sel else (140, 140, 140),
                               (cr.x + 16, cr.centery), 6)
        elif val == 'black':
            pygame.draw.circle(screen, (50, 50, 55) if sel else (80, 80, 80),
                               (cr.x + 16, cr.centery), 6)
            pygame.draw.circle(screen, (120, 120, 125), (cr.x + 16, cr.centery), 6, 1)
        else:
            pygame.draw.circle(screen, (220, 220, 215), (cr.x + 13, cr.centery), 4)
            pygame.draw.circle(screen, (50, 50, 55), (cr.x + 19, cr.centery), 4)
            pygame.draw.circle(screen, (120, 120, 125), (cr.x + 19, cr.centery), 4, 1)
        t = F.FONT_SM.render(lbl, True, (240, 240, 235) if sel else (150, 150, 155))
        screen.blit(t, (cr.x + 30, cr.y + 9))
    y += 46

    # === DIFFICULTY ===
    screen.blit(F.FONT_B.render("Difficulty", True, (200, 200, 205)), (sx, y))
    y += 24
    names = ['Beginner', 'Novice', 'Casual', 'Easy', 'Medium',
             'Intermediate', 'Strong', 'Advanced', 'Expert', 'Master']
    bh, gap = 26, 3
    row_w = section_w
    cols = 2
    col_w = (row_w - 8) // cols
    game.menu_rects = []
    for i in range(10):
        col_idx = i % cols
        row_idx = i // cols
        rect = pygame.Rect(sx + col_idx * (col_w + 8), y + row_idx * (bh + gap), col_w, bh)
        game.menu_rects.append((rect, i + 1))
        hover = rect.collidepoint(mx, my)
        sel = not game.adaptive and game.menu_level == i + 1
        if sel:
            pygame.draw.rect(screen, (30, 95, 50), rect, border_radius=5)
            pygame.draw.rect(screen, (81, 190, 95), rect, 2, border_radius=5)
        elif hover:
            pygame.draw.rect(screen, (42, 42, 48), rect, border_radius=5)
        else:
            pygame.draw.rect(screen, (30, 30, 36), rect, border_radius=5)
        t = F.FONT_SM.render(names[i], True,
                             (240, 240, 235) if sel else (140, 140, 145))
        screen.blit(t, (rect.x + 10, rect.y + 6))
        total_stars = 5
        star_x = rect.right - total_stars * 11 - 4
        filled = (i + 1) // 2
        has_hollow = (i + 1) % 2
        fc = (81, 190, 95) if sel else (60, 65, 62)
        hc = (81, 190, 95, 120) if sel else (45, 48, 45)
        for s in range(total_stars):
            cx = star_x + s * 11 + 5
            cy = rect.centery
            pts = _star_points(cx, cy, 4, 2)
            if s < filled:
                pygame.draw.polygon(screen, fc, pts)
            elif s == filled and has_hollow:
                pygame.draw.polygon(screen, hc, pts, 1)
            else:
                pygame.draw.polygon(screen, (35, 38, 35), pts)

    rows_needed = (10 + cols - 1) // cols
    y += rows_needed * (bh + gap) + 4

    # Adaptive toggle
    ar = pygame.Rect(sx, y, section_w, bh + 2)
    game.adaptive_rect = ar
    if game.adaptive:
        pygame.draw.rect(screen, (65, 50, 10), ar, border_radius=5)
        pygame.draw.rect(screen, (200, 160, 50), ar, 2, border_radius=5)
    else:
        bg = (42, 42, 48) if ar.collidepoint(mx, my) else (30, 30, 36)
        pygame.draw.rect(screen, bg, ar, border_radius=5)
    at = F.FONT_SM.render(f"Adaptive Mode (Level {game.adaptive_level})", True,
                          (240, 195, 80) if game.adaptive else (130, 130, 135))
    screen.blit(at, (ar.x + 12, ar.y + 7))
    tog_x = ar.right - 38
    tog_w, tog_h = 28, 14
    tog_r = pygame.Rect(tog_x, ar.centery - tog_h // 2, tog_w, tog_h)
    if game.adaptive:
        pygame.draw.rect(screen, (200, 160, 50), tog_r, border_radius=7)
        pygame.draw.circle(screen, (255, 255, 255), (tog_r.right - 7, tog_r.centery), 5)
    else:
        pygame.draw.rect(screen, (60, 60, 65), tog_r, border_radius=7)
        pygame.draw.circle(screen, (100, 100, 105), (tog_r.x + 7, tog_r.centery), 5)
    y += bh + 14

    # === TIME CONTROL ===
    screen.blit(F.FONT_B.render("Time Control", True, (200, 200, 205)), (sx, y))
    y += 24
    tcbw = (section_w - 8) // 2
    tcbh, tcgap, tc_cols = 26, 3, 2
    game.tc_rects = []
    for ti, (tname, _, _) in enumerate(TIME_CONTROLS):
        tr_row, tc_col = ti // tc_cols, ti % tc_cols
        tcr = pygame.Rect(sx + tc_col * (tcbw + 8), y + tr_row * (tcbh + tcgap), tcbw, tcbh)
        game.tc_rects.append((tcr, ti))
        sel = game.tc_idx == ti
        hover = tcr.collidepoint(mx, my)
        display_name = tname.replace('\u221e', 'No Limit')
        if sel:
            pygame.draw.rect(screen, (30, 95, 50), tcr, border_radius=5)
            pygame.draw.rect(screen, (81, 190, 95), tcr, 2, border_radius=5)
        elif hover:
            pygame.draw.rect(screen, (42, 42, 48), tcr, border_radius=5)
        else:
            pygame.draw.rect(screen, (30, 30, 36), tcr, border_radius=5)
        t = F.FONT_SM.render(display_name, True, (240, 240, 235) if sel else (140, 140, 145))
        screen.blit(t, t.get_rect(center=tcr.center))

    tc_rows = (len(TIME_CONTROLS) + tc_cols - 1) // tc_cols
    y += tc_rows * (tcbh + tcgap) + 14

    # === BOARD THEME + COACH (inline row) ===
    screen.blit(F.FONT_B.render("Theme", True, (200, 200, 205)), (sx, y))
    y += 22
    game.theme_rects = []
    thw = 36
    for i, tn in enumerate(THEME_NAMES):
        tl, td = THEMES[tn]
        tr = pygame.Rect(sx + i * (thw + 6), y, thw, 24)
        game.theme_rects.append((tr, tn))
        sel = game.theme_name == tn
        pygame.draw.rect(screen, tl, (tr.x, tr.y, thw // 2, 24), border_radius=3)
        pygame.draw.rect(screen, td, (tr.x + thw // 2, tr.y, thw // 2, 24), border_radius=3)
        if sel:
            pygame.draw.rect(screen, (81, 190, 95), tr, 2, border_radius=4)

    # Coach toggle on same row, right-aligned
    coach_w = 110
    coach_r = pygame.Rect(sx + section_w - coach_w, y - 2, coach_w, 28)
    game.coach_rect = coach_r
    coach_on = game.menu_coach
    hover_c = coach_r.collidepoint(mx, my)
    if coach_on:
        pygame.draw.rect(screen, (30, 80, 45), coach_r, border_radius=6)
        pygame.draw.rect(screen, (81, 190, 95), coach_r, 2, border_radius=6)
    elif hover_c:
        pygame.draw.rect(screen, (42, 42, 48), coach_r, border_radius=6)
    else:
        pygame.draw.rect(screen, (30, 30, 36), coach_r, border_radius=6)
    clbl = "Coach ON" if coach_on else "Coach OFF"
    ct = F.FONT_SM.render(clbl, True, (140, 230, 155) if coach_on else (120, 120, 125))
    screen.blit(ct, ct.get_rect(center=coach_r.center))

    # --- PLAY BUTTON ---
    btn_w = min(280, section_w)
    btn_h = 52
    btn_y = H - btn_h - 18
    pr = pygame.Rect(cx - btn_w // 2, btn_y, btn_w, btn_h)
    game.play_rect = pr
    hover_play = pr.collidepoint(mx, my)
    base = (55, 185, 80) if hover_play else (42, 160, 65)
    pygame.draw.rect(screen, base, pr, border_radius=10)
    if hover_play:
        glow = pygame.Surface((pr.w + 10, pr.h + 10), pygame.SRCALPHA)
        pygame.draw.rect(glow, (81, 200, 100, 50), (0, 0, pr.w + 10, pr.h + 10), 3, border_radius=12)
        screen.blit(glow, (pr.x - 5, pr.y - 5))
    pt = F.FONT_LG.render("Play", True, (255, 255, 255))
    screen.blit(pt, pt.get_rect(center=pr.center))

    pygame.display.flip()
