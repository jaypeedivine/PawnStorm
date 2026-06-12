import math
import chess
import random
import threading
from config import COACH_COLORS, COACH_SYMBOLS, COACH_NAMES

TIPS_OPENING = [
    "Control the center with pawns.",
    "Develop knights before bishops.",
    "Castle early for king safety.",
    "Don't move the same piece twice.",
    "Connect your rooks.",
]
TIPS_MIDDLEGAME = [
    "Look for forks, pins, and skewers.",
    "Trade when ahead in material.",
    "Place rooks on open files.",
    "Create a plan \u2014 don't drift.",
]
TIPS_ENDGAME = [
    "Activate your king.",
    "Push passed pawns forward.",
    "Centralize everything.",
]


class Coach:
    def __init__(self, ai):
        self.ai = ai
        self.eval_history = [0]
        self.annotations = {}
        self.better_moves = {}
        self.positions = []
        self.last_feedback = None
        self.feedback_timer = 0
        self.eval_display = 0.5
        self.active = False
        self.enabled = False
        self.tip = None
        self.tip_timer = 0
        self.accuracy_scores = []

    def find_best_before(self, board):
        pass

    def record_and_rate(self, board_after, half_idx, player_color, is_player, before_fen=None):
        ev = self.ai.quick_eval(board_after)
        self.eval_history.append(ev)
        if not is_player or not self.enabled:
            return
        if len(self.eval_history) < 2:
            return
        ev_before = self.eval_history[-2]
        delta = (ev - ev_before) if player_color == chess.WHITE else -(ev - ev_before)
        if delta > 60: rating = 'brilliant'
        elif delta > 20: rating = 'great'
        elif delta > -10: rating = 'good'
        elif delta > -30: rating = 'ok'
        elif delta > -80: rating = 'inaccuracy'
        elif delta > -200: rating = 'mistake'
        else: rating = 'blunder'
        self.annotations[half_idx] = rating
        self.accuracy_scores.append(rating)
        if rating in ('inaccuracy', 'mistake', 'blunder') and before_fen:
            self._find_better_async(before_fen, half_idx)
        if rating in COACH_NAMES:
            self.last_feedback = rating
            self.feedback_timer = 180
        if before_fen:
            self._generate_tip(board_after, player_color)

    def _find_better_async(self, fen, half_idx):
        def work():
            board = chess.Board(fen)
            mv = self.ai.get_move(board)
            if mv:
                try:
                    san = board.san(mv)
                except Exception:
                    san = str(mv)
                self.better_moves[half_idx] = (mv, san)
        threading.Thread(target=work, daemon=True).start()

    def _generate_tip(self, board, player_color):
        piece_count = sum(1 for sq in chess.SQUARES if board.piece_at(sq))
        move_num = len(board.move_stack) // 2
        if move_num < 8:
            developed = sum(1 for sq in chess.SQUARES
                          if board.piece_at(sq)
                          and board.piece_at(sq).color == player_color
                          and board.piece_at(sq).piece_type in (chess.KNIGHT, chess.BISHOP)
                          and chess.square_rank(sq) != (0 if player_color == chess.WHITE else 7))
            if developed < 2 and move_num > 2:
                self.tip = "Develop your knights and bishops."
                self.tip_timer = 180
                return
            if board.has_castling_rights(player_color) and move_num > 5:
                self.tip = "Consider castling soon."
                self.tip_timer = 180
                return
            tips = TIPS_OPENING
        elif piece_count > 14:
            tips = TIPS_MIDDLEGAME
        else:
            tips = TIPS_ENDGAME
        self.tip = random.choice(tips)
        self.tip_timer = 180

    def get_eval_pct(self):
        if not self.eval_history:
            return 0.5
        raw = 1.0 / (1.0 + math.exp(-self.eval_history[-1] / 400.0))
        self.eval_display += (raw - self.eval_display) * 0.06
        return self.eval_display

    def get_accuracy(self):
        if not self.accuracy_scores:
            return 0.0
        weights = {'brilliant': 100, 'great': 95, 'good': 85, 'ok': 60,
                   'inaccuracy': 40, 'mistake': 15, 'blunder': 0}
        total = sum(weights.get(r, 50) for r in self.accuracy_scores)
        return total / len(self.accuracy_scores)

    def get_review_data(self, move_stack_san):
        result = []
        for i in range(0, len(move_stack_san), 2):
            num = i // 2 + 1
            w_san = move_stack_san[i]
            b_san = move_stack_san[i + 1] if i + 1 < len(move_stack_san) else ""
            w_ann = self.annotations.get(i, '')
            b_ann = self.annotations.get(i + 1, '')
            w_better = self.better_moves.get(i)
            b_better = self.better_moves.get(i + 1)
            result.append({
                'num': num,
                'w_san': w_san, 'b_san': b_san,
                'w_ann': w_ann, 'b_ann': b_ann,
                'w_better': w_better[1] if w_better else None,
                'b_better': b_better[1] if b_better else None,
            })
        return result

    def reset(self):
        self.eval_history = [0]
        self.annotations = {}
        self.better_moves = {}
        self.positions = []
        self.last_feedback = None
        self.feedback_timer = 0
        self.eval_display = 0.5
        self.tip = None
        self.tip_timer = 0
        self.accuracy_scores = []
