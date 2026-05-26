import chess
import random
from config import PIECE_VAL, PST

class ChessAI:
    DEPTH_MAP = [1,1,2,2,3,3,3,4,4,5]

    def __init__(self, level=5):
        self.level = level
        self.depth = self.DEPTH_MAP[level - 1]

    def set_level(self, lv):
        self.level = lv
        self.depth = self.DEPTH_MAP[lv - 1]

    def evaluate(self, board):
        if board.is_checkmate():
            return -99999 if board.turn == chess.WHITE else 99999
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        sc = 0
        for sq in chess.SQUARES:
            pc = board.piece_at(sq)
            if pc:
                v = PIECE_VAL[pc.piece_type]
                pst = PST.get(pc.piece_type)
                if pst:
                    idx = sq if pc.color == chess.WHITE else chess.square_mirror(sq)
                    v += pst[idx]
                sc += v if pc.color == chess.WHITE else -v
        if self.level >= 5:
            sc += len(list(board.legal_moves)) * (3 if board.turn == chess.WHITE else -3)
        return sc

    def quick_eval(self, board):
        if board.is_checkmate():
            return -99999 if board.turn == chess.WHITE else 99999
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        sc = 0
        for sq in chess.SQUARES:
            pc = board.piece_at(sq)
            if pc:
                v = PIECE_VAL[pc.piece_type]
                pst = PST.get(pc.piece_type)
                if pst:
                    idx = sq if pc.color == chess.WHITE else chess.square_mirror(sq)
                    v += pst[idx]
                sc += v if pc.color == chess.WHITE else -v
        return sc

    def _move_priority(self, board, move):
        sc = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim and attacker:
                sc += PIECE_VAL[victim.piece_type] - PIECE_VAL[attacker.piece_type] // 10
            else:
                sc += 50
        if move.promotion:
            sc += 800
        pc = board.piece_at(move.from_square)
        if pc:
            pst = PST.get(pc.piece_type)
            if pst:
                fr = move.from_square if board.turn == chess.WHITE else chess.square_mirror(move.from_square)
                to = move.to_square if board.turn == chess.WHITE else chess.square_mirror(move.to_square)
                sc += pst[to] - pst[fr]
        return sc

    def alphabeta(self, board, depth, alpha, beta, maximizing):
        if depth == 0 or board.is_game_over():
            return self.evaluate(board)
        moves = list(board.legal_moves)
        if self.level >= 4:
            moves.sort(key=lambda m: self._move_priority(board, m), reverse=True)
        if maximizing:
            val = -float('inf')
            for m in moves:
                board.push(m)
                val = max(val, self.alphabeta(board, depth-1, alpha, beta, False))
                board.pop()
                alpha = max(alpha, val)
                if beta <= alpha:
                    break
            return val
        else:
            val = float('inf')
            for m in moves:
                board.push(m)
                val = min(val, self.alphabeta(board, depth-1, alpha, beta, True))
                board.pop()
                beta = min(beta, val)
                if beta <= alpha:
                    break
            return val

    def get_move(self, board):
        moves = list(board.legal_moves)
        if not moves:
            return None
        maximizing = board.turn == chess.WHITE
        scored = []
        for m in moves:
            board.push(m)
            sc = self.alphabeta(board, self.depth - 1, -float('inf'), float('inf'), not maximizing)
            board.pop()
            scored.append((sc, m))
        scored.sort(key=lambda x: x[0], reverse=maximizing)
        if self.level <= 1:
            return random.choice(scored[:min(5, len(scored))])[1]
        elif self.level <= 3:
            return random.choice(scored[:min(3, len(scored))])[1]
        return scored[0][1]
