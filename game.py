import pygame
import chess
import threading
import time
import random
import sys
from config import (L, F, THEMES, THEME_NAMES, TIME_CONTROLS, AI_THINK_MIN, AI_THINK_JITTER,
                     COACH_COLORS, COACH_SYMBOLS, detect_opening)
from sounds import SND_MOVE, SND_CAP, SND_CHECK, SND_ILLEGAL
import pieces
from ai import ChessAI
from coach import Coach
import renderer

class ChessGame:
    def __init__(self):
        self.portrait = False
        self.panel_below_h = 0
        self.screen = pygame.display.set_mode((L.WIN_W, L.WIN_H), pygame.RESIZABLE)
        pygame.display.set_caption("PawnStorm Chess")
        import os
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pawnstorm_icon.png")
        if os.path.exists(icon_path):
            pygame.display.set_icon(pygame.image.load(icon_path))
        self.clock = pygame.time.Clock()
        self.board = chess.Board()
        self.ai = ChessAI(5)
        self.coach = Coach(self.ai)
        self.coach_mode_idx = 0
        self.player_color = chess.WHITE
        self.flipped = False
        self.selected = None
        self.legal_for_selected = []
        self.dragging = False
        self.drag_piece = None
        self.drag_pos = (0, 0)
        self.drag_from = None
        self.premove = None
        self.ai_thinking = False
        self.ai_thread = None
        self.ai_result = None
        self.ai_think_start = 0
        self.tc_idx = 9
        self.increment = TIME_CONTROLS[self.tc_idx][2]
        base = TIME_CONTROLS[self.tc_idx][1]
        self.white_time = float(base) if base > 0 else float('inf')
        self.black_time = float(base) if base > 0 else float('inf')
        self.last_tick = time.time()
        self.move_stack_san = []
        self.captured_w = []
        self.captured_b = []
        self.last_move = None
        self.game_over = False
        self.game_result = ""
        self.theme_idx = 0
        self.theme_name = THEME_NAMES[0]
        self.state = 'menu'
        self.menu_level = 5
        self.menu_color = 'white'
        self.menu_coach = False
        self.adaptive = False
        self.adaptive_level = 4
        self.consec_wins = 0
        self.consec_losses = 0
        self.promo_pending = None
        self.hint_move = None
        self.hint_timer = 0
        self.anim_piece = None
        self.anim_from = (0, 0)
        self.anim_to = (0, 0)
        self.anim_start = 0
        self.anim_dur = 0.18
        self.anim_is_white = True
        self.anim_sq = None
        self.opening_name = None
        self.scroll_offset = 0
        self.review_scroll = 0
        self.buttons = []
        self._build_buttons()

    def recalc_layout(self, w, h):
        old_sq = L.SQ
        L.WIN_W, L.WIN_H = w, h
        self.portrait = w < h * 0.85 or w < 580
        if self.portrait:
            L.PANEL_W = 0
            max_sq_w = (w - L.EVAL_W) // 8
            max_sq_h = (h - L.TOP_H - L.BOT_H - 80) // 8
            L.SQ = max(28, min(max_sq_w, max_sq_h))
            L.BOARD_PX = L.SQ * 8
            self.panel_below_h = max(0, h - L.TOP_H - L.BOARD_PX - L.BOT_H)
        else:
            L.PANEL_W = max(160, min(235, (w - L.EVAL_W) // 4))
            self.panel_below_h = 0
            max_sq_w = (w - L.EVAL_W - L.PANEL_W) // 8
            max_sq_h = (h - L.TOP_H - L.BOT_H) // 8
            L.SQ = max(28, min(max_sq_w, max_sq_h))
            L.BOARD_PX = L.SQ * 8
        L.BX = L.EVAL_W
        if L.SQ != old_sq:
            pieces.rebuild(L.SQ)
            F.rebuild(L.SQ)
        self.screen = pygame.display.set_mode((L.WIN_W, L.WIN_H), pygame.RESIZABLE)
        self._build_buttons()

    def _build_buttons(self):
        self.buttons = []
        labels = ['Undo', 'Hint', 'Resign', 'New', 'Review', 'Menu']
        bw = max(40, int(L.SQ * 0.88))
        bh = max(22, int(L.SQ * 0.42))
        gap = max(3, int(L.SQ * 0.08))
        total = len(labels) * bw + (len(labels)-1) * gap
        sx = L.BX + (L.BOARD_PX - total) // 2
        btn_y = L.TOP_H + L.BOARD_PX + (L.BOT_H - bh) // 2
        for i, lb in enumerate(labels):
            self.buttons.append((pygame.Rect(sx + i*(bw+gap), btn_y, bw, bh), lb))

    def sq_to_px(self, sq):
        c, r = chess.square_file(sq), chess.square_rank(sq)
        if self.flipped:
            return L.BX + (7-c)*L.SQ, L.TOP_H + r*L.SQ
        return L.BX + c*L.SQ, L.TOP_H + (7-r)*L.SQ

    def px_to_sq(self, x, y):
        bx, by = x - L.BX, y - L.TOP_H
        if bx < 0 or bx >= L.BOARD_PX or by < 0 or by >= L.BOARD_PX:
            return None
        c, r = bx // L.SQ, by // L.SQ
        if self.flipped:
            c = 7 - c
        else:
            r = 7 - r
        return chess.square(c, r)

    def _is_player_turn(self):
        return self.board.turn == self.player_color and not self.game_over

    def handle_mouse_down(self, pos):
        if self.promo_pending:
            self._handle_promo_click(pos)
            return
        sq = self.px_to_sq(pos[0], pos[1])
        if sq is None:
            return
        if self.ai_thinking:
            pc = self.board.piece_at(sq)
            if pc and pc.color == self.player_color:
                self.premove = None
                self.selected = sq
                self.dragging = True
                self.drag_from = sq
                self.drag_piece = pc
                self.drag_pos = pos
            elif self.selected is not None:
                self.premove = (self.selected, sq)
                self.selected = None
            return
        if not self._is_player_turn():
            return
        pc = self.board.piece_at(sq)
        if self.selected is not None:
            if sq == self.selected:
                self.selected = None
                self.legal_for_selected = []
                return
            if pc and pc.color == self.player_color:
                self.selected = sq
                self.legal_for_selected = [m for m in self.board.legal_moves if m.from_square == sq]
                self.dragging = True
                self.drag_from = sq
                self.drag_piece = pc
                self.drag_pos = pos
                return
            self._try_move(self.selected, sq)
            return
        if pc and pc.color == self.player_color:
            self.selected = sq
            self.legal_for_selected = [m for m in self.board.legal_moves if m.from_square == sq]
            self.dragging = True
            self.drag_from = sq
            self.drag_piece = pc
            self.drag_pos = pos

    def handle_mouse_up(self, pos):
        if not self.dragging:
            return
        self.dragging = False
        sq = self.px_to_sq(pos[0], pos[1])
        if sq is not None and sq != self.drag_from:
            if self.ai_thinking:
                self.premove = (self.drag_from, sq)
                self.selected = None
            else:
                self._try_move(self.drag_from, sq)
        self.drag_piece = None
        self.drag_from = None

    def handle_mouse_motion(self, pos):
        if self.dragging:
            self.drag_pos = pos

    def _try_move(self, fr, to):
        pc = self.board.piece_at(fr)
        if pc and pc.piece_type == chess.PAWN:
            rank = chess.square_rank(to)
            if (pc.color == chess.WHITE and rank == 7) or (pc.color == chess.BLACK and rank == 0):
                self.promo_pending = (fr, to)
                self.selected = None
                self.legal_for_selected = []
                return
        move = chess.Move(fr, to)
        if move in self.board.legal_moves:
            self._do_move(move)
        else:
            SND_ILLEGAL.play()
        self.selected = None
        self.legal_for_selected = []

    def _handle_promo_click(self, pos):
        cx = L.BX + L.BOARD_PX // 2
        cy = L.TOP_H + L.BOARD_PX // 2
        for i, pt in enumerate([chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]):
            r = pygame.Rect(cx - 100 + i*55, cy - 25, 48, 48)
            if r.collidepoint(pos):
                fr, to = self.promo_pending
                move = chess.Move(fr, to, promotion=pt)
                if move in self.board.legal_moves:
                    self._do_move(move)
                self.promo_pending = None
                return

    def _do_move(self, move):
        is_player = self.board.turn == self.player_color
        if is_player and self.coach.enabled:
            self.coach.find_best_before(self.board)
        cap = self.board.piece_at(move.to_square)
        san = self.board.san(move)
        pc = self.board.piece_at(move.from_square)
        if pc:
            self.anim_piece = pc.piece_type
            self.anim_is_white = pc.color == chess.WHITE
            self.anim_from = self.sq_to_px(move.from_square)
            self.anim_to = self.sq_to_px(move.to_square)
            self.anim_start = time.time()
            self.anim_sq = move.to_square
        before_fen = self.board.fen()
        self.coach.positions.append(before_fen)
        self.board.push(move)
        half_idx = len(self.board.move_stack) - 1
        self.coach.record_and_rate(self.board, half_idx, self.player_color, is_player, before_fen)
        if self.increment > 0 and len(self.board.move_stack) > 1:
            if self.board.turn == chess.BLACK:
                self.white_time += self.increment
            else:
                self.black_time += self.increment
        self.move_stack_san.append(san)
        self.last_move = move
        self.hint_move = None
        self.opening_name = detect_opening(self.board) or self.opening_name
        if cap:
            lst = self.captured_w if cap.color == chess.WHITE else self.captured_b
            lst.append(cap.symbol().upper())
            SND_CAP.play()
        elif self.board.is_check():
            SND_CHECK.play()
        else:
            SND_MOVE.play()
        self._check_game_over()
        if not self.game_over and self.board.turn != self.player_color:
            self._start_ai()

    def _start_ai(self):
        self.ai_thinking = True
        self.ai_result = None
        self.ai_think_start = time.time()
        self.ai_thread = threading.Thread(target=self._ai_worker, daemon=True)
        self.ai_thread.start()

    def _ai_worker(self):
        t0 = time.time()
        board_copy = self.board.copy()
        ai_time = self.black_time if self.board.turn == chess.BLACK else self.white_time
        move_num = len(self.board.move_stack) // 2

        pressure = self._time_pressure(ai_time)
        orig_depth = self.ai.depth
        if pressure > 0.7:
            self.ai.depth = max(1, orig_depth - 2)
        elif pressure > 0.4:
            self.ai.depth = max(1, orig_depth - 1)

        move = self.ai.get_move(board_copy)
        self.ai.depth = orig_depth

        target = self._smart_delay(ai_time, move_num, board_copy, pressure)
        wait = target - (time.time() - t0)
        if wait > 0:
            time.sleep(wait)
        self.ai_result = move

    def _time_pressure(self, ai_time):
        if ai_time == float('inf'):
            return 0.0
        if ai_time <= 5:
            return 0.9
        elif ai_time <= 15:
            return 0.7
        elif ai_time <= 30:
            return 0.4
        elif ai_time <= 60:
            return 0.2
        return 0.0

    def _smart_delay(self, ai_time, move_num, board, pressure):
        base = AI_THINK_MIN[self.ai.level - 1]

        if ai_time == float('inf'):
            return max(0.5, base + random.uniform(-AI_THINK_JITTER, AI_THINK_JITTER))

        if move_num < 4:
            delay = random.uniform(0.3, 0.8)
        elif move_num < 10:
            delay = base * random.uniform(0.6, 1.0)
        else:
            delay = base + random.uniform(-AI_THINK_JITTER, AI_THINK_JITTER)

        is_capture = any(board.is_capture(m) for m in list(board.legal_moves)[:5])
        if board.is_check():
            delay *= 0.5
        elif is_capture:
            delay *= random.uniform(0.5, 0.8)

        num_legal = len(list(board.legal_moves))
        if num_legal <= 3:
            delay *= 0.4
        elif num_legal > 25:
            delay *= random.uniform(1.1, 1.4)

        if pressure > 0.7:
            delay = random.uniform(0.1, 0.4)
        elif pressure > 0.4:
            delay *= 0.4
        elif pressure > 0.2:
            delay *= 0.7

        max_spend = ai_time * 0.08
        delay = min(delay, max_spend)

        return max(0.15, delay)

    def _apply_ai_move(self):
        move = self.ai_result
        self.ai_result = None
        self.ai_thinking = False
        if move and move in self.board.legal_moves:
            self._do_move(move)
        if self.premove and not self.game_over:
            fr, to = self.premove
            self.premove = None
            mv = chess.Move(fr, to)
            if mv in self.board.legal_moves:
                self._do_move(mv)
            else:
                promos = [m for m in self.board.legal_moves if m.from_square == fr and m.to_square == to]
                if promos:
                    self._do_move(promos[0])

    def _check_game_over(self):
        if not self.board.is_game_over():
            return
        self.game_over = True
        res = self.board.result()
        if res == '1-0':
            won = self.player_color == chess.WHITE
            self.game_result = "You win!" if won else "You lose!"
            self._adapt_win() if won else self._adapt_loss()
        elif res == '0-1':
            won = self.player_color == chess.BLACK
            self.game_result = "You win!" if won else "You lose!"
            self._adapt_win() if won else self._adapt_loss()
        else:
            self.game_result = "Draw!"
            self.consec_wins = self.consec_losses = 0

    def _adapt_win(self):
        if not self.adaptive:
            return
        self.consec_wins += 1
        self.consec_losses = 0
        if self.consec_wins >= 1:
            self.adaptive_level = min(10, self.adaptive_level + 1)
            self.ai.set_level(self.adaptive_level)
            self.consec_wins = 0

    def _adapt_loss(self):
        if not self.adaptive:
            return
        self.consec_losses += 1
        self.consec_wins = 0
        if self.consec_losses >= 2:
            self.adaptive_level = max(1, self.adaptive_level - 1)
            self.ai.set_level(self.adaptive_level)
            self.consec_losses = 0

    def undo(self):
        if len(self.board.move_stack) < 2 or self.ai_thinking:
            return
        idx1 = len(self.board.move_stack) - 1
        idx2 = len(self.board.move_stack) - 2
        self.board.pop()
        self.board.pop()
        if len(self.move_stack_san) >= 2:
            self.move_stack_san.pop()
            self.move_stack_san.pop()
        if len(self.coach.eval_history) > 2:
            self.coach.eval_history.pop()
            self.coach.eval_history.pop()
        self.coach.annotations.pop(idx1, None)
        self.coach.annotations.pop(idx2, None)
        self.coach.better_moves.pop(idx1, None)
        self.coach.better_moves.pop(idx2, None)
        self.last_move = self.board.peek() if self.board.move_stack else None
        self.game_over = False
        self.game_result = ""
        self.selected = None
        self.legal_for_selected = []
        self.premove = None
        self.hint_move = None

    def resign(self):
        if self.game_over or not self.board.move_stack:
            return
        self.game_over = True
        winner = "Black" if self.player_color == chess.WHITE else "White"
        self.game_result = f"{winner} wins by resignation"
        self._adapt_loss()

    def hint(self):
        if self.ai_thinking or self.game_over or not self._is_player_turn():
            return
        h = ChessAI(min(self.ai.level + 1, 10))
        mv = h.get_move(self.board.copy())
        if mv:
            self.hint_move = mv
            self.hint_timer = 90

    def new_game(self):
        self.board = chess.Board()
        if self.menu_color == 'random':
            self.player_color = random.choice([chess.WHITE, chess.BLACK])
        elif self.menu_color == 'black':
            self.player_color = chess.BLACK
        else:
            self.player_color = chess.WHITE
        self.flipped = self.player_color == chess.BLACK
        self.selected = None
        self.legal_for_selected = []
        self.dragging = False
        self.drag_piece = None
        self.premove = None
        self.ai_thinking = False
        self.ai_result = None
        self.increment = TIME_CONTROLS[self.tc_idx][2]
        base = TIME_CONTROLS[self.tc_idx][1]
        self.white_time = float(base) if base > 0 else float('inf')
        self.black_time = float(base) if base > 0 else float('inf')
        self.last_tick = time.time()
        self.move_stack_san = []
        self.captured_w = []
        self.captured_b = []
        self.last_move = None
        self.game_over = False
        self.game_result = ""
        self.promo_pending = None
        self.hint_move = None
        self.anim_piece = None
        self.anim_sq = None
        self.opening_name = None
        self.scroll_offset = 0
        self.review_scroll = 0
        self.coach.reset()
        self.coach.active = self.menu_coach
        self.coach.enabled = self.menu_coach
        if self.player_color != chess.WHITE:
            self._start_ai()

    def cycle_theme(self):
        self.theme_idx = (self.theme_idx + 1) % len(THEME_NAMES)
        self.theme_name = THEME_NAMES[self.theme_idx]

    def handle_button(self, pos):
        for rect, label in self.buttons:
            if rect.collidepoint(pos):
                if label == 'Undo': self.undo()
                elif label == 'Hint': self.hint()
                elif label == 'Resign': self.resign()
                elif label == 'New': self.new_game()
                elif label == 'Review':
                    if self.game_over and self.move_stack_san:
                        self.start_review()
                elif label == 'Review':
                    if self.game_over and self.move_stack_san:
                        self.start_review()
                elif label == 'Theme': self.cycle_theme()
                elif label == 'Menu': self.state = 'menu'
                return True
        return False

    def handle_scroll(self, y):
        if self.state == 'review':
            review_data = self.coach.get_review_data(self.move_stack_san)
            max_scroll = max(0, len(review_data) - 12)
            self.review_scroll = max(0, min(max_scroll, self.review_scroll - y))
        else:
            max_lines = max(0, len(self.move_stack_san) // 2 - 15)
            self.scroll_offset = max(0, min(max_lines, self.scroll_offset - y))

    def start_review(self):
        self.state = 'review'
        self.review_moves = list(self.board.move_stack)
        self.review_idx = len(self.review_moves)
        self.review_scroll = 0
        self._rebuild_review_board()

    def _rebuild_review_board(self):
        b = chess.Board()
        for i in range(self.review_idx):
            b.push(self.review_moves[i])
        self.review_board = b

    def review_step(self, delta):
        new_idx = max(0, min(len(self.review_moves), self.review_idx + delta))
        if new_idx != self.review_idx:
            self.review_idx = new_idx
            self._rebuild_review_board()

    def get_review_comment(self):
        if self.review_idx == 0:
            return "Starting position.", (150, 150, 155)
        half_idx = self.review_idx - 1
        ann = self.coach.annotations.get(half_idx, '')
        move_san = self.move_stack_san[half_idx] if half_idx < len(self.move_stack_san) else ''
        move_num = half_idx // 2 + 1
        is_white = half_idx % 2 == 0
        side = "White" if is_white else "Black"
        better = self.coach.better_moves.get(half_idx)
        if ann == 'blunder':
            msg = f"{side} played {move_san} — a blunder!"
            if better:
                msg += f" Better was {better[1]}."
            return msg, COACH_COLORS['blunder']
        elif ann == 'mistake':
            msg = f"{side} played {move_san} — a mistake."
            if better:
                msg += f" {better[1]} was stronger."
            return msg, COACH_COLORS['mistake']
        elif ann == 'inaccuracy':
            msg = f"{side} played {move_san} — slightly inaccurate."
            if better:
                msg += f" Consider {better[1]}."
            return msg, COACH_COLORS['inaccuracy']
        elif ann == 'brilliant':
            return f"{side} played {move_san} — brilliant!!", COACH_COLORS['brilliant']
        elif ann == 'great':
            return f"{side} played {move_san} — great move!", COACH_COLORS['great']
        elif ann in ('good', 'ok'):
            return f"{move_num}. {'...' if not is_white else ''}{move_san}", (150, 150, 155)
        else:
            return f"{move_num}. {'...' if not is_white else ''}{move_san}", (150, 150, 155)

    def handle_review_click(self, pos):
        if hasattr(self, 'review_nav'):
            for rect, action in self.review_nav:
                if rect.collidepoint(pos):
                    if action == 'start': self.review_step(-999)
                    elif action == 'back': self.review_step(-1)
                    elif action == 'fwd': self.review_step(1)
                    elif action == 'end': self.review_step(999)
                    elif action == 'exit': self.state = 'playing'
                    elif action == 'menu': self.state = 'menu'
                    return
        if hasattr(self, 'review_move_rects'):
            for rect, idx in self.review_move_rects:
                if rect.collidepoint(pos):
                    self.review_idx = idx
                    self._rebuild_review_board()
                    return

    def handle_menu_click(self, pos):
        if hasattr(self, 'menu_rects'):
            for rect, lv in self.menu_rects:
                if rect.collidepoint(pos):
                    self.menu_level = lv
                    self.adaptive = False
                    return
        if hasattr(self, 'adaptive_rect') and self.adaptive_rect.collidepoint(pos):
            self.adaptive = True
            return
        if hasattr(self, 'color_rects'):
            for rect, val in self.color_rects:
                if rect.collidepoint(pos):
                    self.menu_color = val
                    return
        if hasattr(self, 'tc_rects'):
            for rect, idx in self.tc_rects:
                if rect.collidepoint(pos):
                    self.tc_idx = idx
                    return
        if hasattr(self, 'theme_rects'):
            for rect, tn in self.theme_rects:
                if rect.collidepoint(pos):
                    self.theme_name = tn
                    self.theme_idx = THEME_NAMES.index(tn)
                    return
        if hasattr(self, 'coach_rect') and self.coach_rect.collidepoint(pos):
            self.menu_coach = not self.menu_coach
            return
        if hasattr(self, 'coach_rects'):
            for rect, idx in self.coach_rects:
                if rect.collidepoint(pos):
                    self.coach_mode_idx = idx
                    self.coach.active = idx == 1
                    self.coach.enabled = idx == 1
                    return
        if hasattr(self, 'play_rect') and self.play_rect.collidepoint(pos):
            self.ai.set_level(self.adaptive_level if self.adaptive else self.menu_level)
            self.state = 'playing'
            self.new_game()
            self.last_tick = time.time()

    def update(self):
        now = time.time()
        if not self.game_over and self.board.move_stack:
            dt = now - self.last_tick
            if self.board.turn == chess.WHITE:
                self.white_time = max(0, self.white_time - dt)
                if self.white_time <= 0:
                    self.game_over = True
                    self.game_result = "Time out!" if self.player_color == chess.WHITE else "Opponent flagged!"
            else:
                self.black_time = max(0, self.black_time - dt)
                if self.black_time <= 0:
                    self.game_over = True
                    self.game_result = "Time out!" if self.player_color == chess.BLACK else "Opponent flagged!"
        self.last_tick = now
        if self.ai_thinking and self.ai_result is not None:
            self._apply_ai_move()
        if self.coach.feedback_timer > 0:
            self.coach.feedback_timer -= 1
        if self.coach.tip_timer > 0:
            self.coach.tip_timer -= 1
            if self.coach.tip_timer <= 0:
                self.coach.tip = None
        if self.hint_timer > 0:
            self.hint_timer -= 1
            if self.hint_timer <= 0:
                self.hint_move = None

    def draw_game(self):
        self.screen.fill((32,32,36))
        renderer.draw_eval_bar(self, self.screen)
        renderer.draw_board(self, self.screen)
        renderer.draw_highlights(self, self.screen)
        renderer.draw_better_move_arrow(self, self.screen)
        renderer.draw_pieces(self, self.screen)
        renderer.draw_thinking(self, self.screen)
        renderer.draw_top_bar(self, self.screen)
        renderer.draw_bottom_bar(self, self.screen)
        renderer.draw_side_panel(self, self.screen)
        renderer.draw_coach_feedback(self, self.screen)
        renderer.draw_coach_tip(self, self.screen)
        if self.promo_pending:
            renderer.draw_promo_dialog(self, self.screen)
        renderer.draw_game_over(self, self.screen)
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.recalc_layout(event.w, event.h)
                elif event.type == pygame.KEYDOWN:
                    if self.state == 'review':
                        if event.key == pygame.K_LEFT:
                            self.review_step(-1)
                        elif event.key == pygame.K_RIGHT:
                            self.review_step(1)
                        elif event.key == pygame.K_HOME:
                            self.review_step(-999)
                        elif event.key == pygame.K_END:
                            self.review_step(999)
                        elif event.key in (pygame.K_ESCAPE, getattr(pygame, 'K_AC_BACK', pygame.K_ESCAPE)):
                            self.state = 'playing'
                    elif event.key in (pygame.K_ESCAPE, getattr(pygame, 'K_AC_BACK', pygame.K_ESCAPE)):
                        if self.state == 'playing':
                            self.premove = None
                        elif self.state == 'menu' and self.board.move_stack:
                            self.state = 'playing'
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.state == 'menu':
                            self.handle_menu_click(event.pos)
                        elif self.state == 'review':
                            self.handle_review_click(event.pos)
                        elif hasattr(self, '_review_btn') and self.game_over and self._review_btn.collidepoint(event.pos):
                            self.start_review()
                        elif not self.handle_button(event.pos):
                            self.handle_mouse_down(event.pos)
                    elif event.button in (4, 5):
                        if self.state == 'review':
                            self.review_step(1 if event.button == 4 else -1)
                        else:
                            self.handle_scroll(1 if event.button == 4 else -1)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.state == 'playing':
                        self.handle_mouse_up(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    if self.state == 'playing':
                        self.handle_mouse_motion(event.pos)
            if self.state == 'menu':
                renderer.draw_menu(self, self.screen)
            elif self.state == 'review':
                renderer.draw_review(self, self.screen)
                pygame.display.flip()
            else:
                self.update()
                self.draw_game()
            self.clock.tick(60)
        pygame.quit()
        sys.exit()
