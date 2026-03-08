import copy
import math
import random
from dataclasses import dataclass


EMPTY = 0
BLACK = 1
WHITE = -1


def opponent(player: int) -> int:
    return -player


def player_name(player: int) -> str:
    return "Black" if player == BLACK else "White"


def rules_name(ruleset: str) -> str:
    return "Japanese" if ruleset == "japanese" else "Chinese"


@dataclass
class MoveResult:
    success: bool
    reason: str = ""
    captured: int = 0
    game_over: bool = False


class GoGame:
    def __init__(self, size: int = 19, ruleset: str = "japanese", komi: float = 6.5):
        self.size = size
        self.ruleset = ruleset
        self.komi = komi
        self.reset()

    def reset(self) -> None:
        self.board = [[EMPTY for _ in range(self.size)] for _ in range(self.size)]
        self.turn = BLACK
        self.captures = {BLACK: 0, WHITE: 0}
        self.pass_count = 0
        self.scoring_mode = False
        self.game_over = False
        self.winner = None
        self.last_move = None
        self.resigned_player = None
        self.move_number = 0
        self.board_history = [self.board_hash()]
        self.state_stack = []
        self.marked_dead = set()

    def clone_state(self):
        return {
            "board": copy.deepcopy(self.board),
            "turn": self.turn,
            "captures": dict(self.captures),
            "pass_count": self.pass_count,
            "scoring_mode": self.scoring_mode,
            "game_over": self.game_over,
            "winner": self.winner,
            "last_move": self.last_move,
            "resigned_player": self.resigned_player,
            "move_number": self.move_number,
            "board_history": list(self.board_history),
            "marked_dead": set(self.marked_dead),
        }

    def restore_state(self, state) -> None:
        self.board = copy.deepcopy(state["board"])
        self.turn = state["turn"]
        self.captures = dict(state["captures"])
        self.pass_count = state["pass_count"]
        self.scoring_mode = state["scoring_mode"]
        self.game_over = state["game_over"]
        self.winner = state["winner"]
        self.last_move = state["last_move"]
        self.resigned_player = state["resigned_player"]
        self.move_number = state["move_number"]
        self.board_history = list(state["board_history"])
        self.marked_dead = set(state["marked_dead"])

    def push_undo_state(self) -> None:
        self.state_stack.append(self.clone_state())

    def undo(self, steps: int = 1) -> bool:
        if len(self.state_stack) < steps:
            return False
        state = None
        for _ in range(steps):
            state = self.state_stack.pop()
        self.restore_state(state)
        return True

    def board_hash(self, board=None):
        target = board if board is not None else self.board
        return tuple(tuple(row) for row in target)

    def on_board(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def neighbors(self, x: int, y: int):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.on_board(nx, ny):
                yield nx, ny

    def group_and_liberties(self, x: int, y: int, board=None):
        target = board if board is not None else self.board
        color = target[y][x]
        if color == EMPTY:
            return set(), set()

        group = set()
        liberties = set()
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in group:
                continue
            group.add((cx, cy))
            for nx, ny in self.neighbors(cx, cy):
                stone = target[ny][nx]
                if stone == EMPTY:
                    liberties.add((nx, ny))
                elif stone == color and (nx, ny) not in group:
                    stack.append((nx, ny))
        return group, liberties

    def remove_group(self, group, board=None) -> None:
        target = board if board is not None else self.board
        for x, y in group:
            target[y][x] = EMPTY

    def is_legal_move(self, x: int, y: int, player=None):
        if player is None:
            player = self.turn
        if self.game_over:
            return False, "The game is already over."
        if self.scoring_mode:
            return False, "Scoring is in progress. Resume play or finalize scoring."
        if not self.on_board(x, y):
            return False, "Move is outside the board."
        if self.board[y][x] != EMPTY:
            return False, "That point is already occupied."

        trial = copy.deepcopy(self.board)
        trial[y][x] = player
        total_captured = 0
        for nx, ny in self.neighbors(x, y):
            if trial[ny][nx] == opponent(player):
                enemy_group, enemy_liberties = self.group_and_liberties(nx, ny, trial)
                if not enemy_liberties:
                    total_captured += len(enemy_group)
                    self.remove_group(enemy_group, trial)

        _, own_liberties = self.group_and_liberties(x, y, trial)
        if not own_liberties:
            return False, "Suicide is not allowed."

        new_hash = self.board_hash(trial)
        if len(self.board_history) >= 2 and new_hash == self.board_history[-2]:
            return False, "Ko: that move repeats the previous board position."

        return True, {"board": trial, "captured": total_captured}

    def play_move(self, x: int, y: int) -> MoveResult:
        self.push_undo_state()
        legal, payload = self.is_legal_move(x, y)
        if not legal:
            self.state_stack.pop()
            return MoveResult(False, payload)

        self.board = payload["board"]
        captured = payload["captured"]
        self.captures[self.turn] += captured
        self.pass_count = 0
        self.last_move = (x, y, self.turn)
        self.move_number += 1
        self.board_history.append(self.board_hash())
        self.turn = opponent(self.turn)
        return MoveResult(True, captured=captured)

    def pass_turn(self) -> MoveResult:
        if self.game_over:
            return MoveResult(False, "The game is already over.")
        if self.scoring_mode:
            return MoveResult(False, "Scoring is in progress. Resume play or finalize scoring.")
        self.push_undo_state()
        current = self.turn
        self.pass_count += 1
        self.last_move = ("pass", current)
        self.move_number += 1
        self.board_history.append(self.board_hash())
        self.turn = opponent(self.turn)
        if self.pass_count >= 2:
            self.scoring_mode = True
            return MoveResult(True)
        return MoveResult(True)

    def resign(self) -> None:
        if self.game_over:
            return
        self.push_undo_state()
        self.resigned_player = self.turn
        self.winner = opponent(self.turn)
        self.game_over = True
        self.scoring_mode = False

    def legal_moves(self, player=None):
        if player is None:
            player = self.turn
        moves = []
        for y in range(self.size):
            for x in range(self.size):
                legal, payload = self.is_legal_move(x, y, player)
                if legal:
                    moves.append((x, y, payload["captured"], payload["board"]))
        return moves

    def territory_map(self):
        visited = set()
        territory = {BLACK: set(), WHITE: set()}
        neutral = set()
        for y in range(self.size):
            for x in range(self.size):
                if self.board[y][x] != EMPTY or (x, y) in visited:
                    continue
                region = set()
                bordering = set()
                stack = [(x, y)]
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in visited:
                        continue
                    visited.add((cx, cy))
                    region.add((cx, cy))
                    for nx, ny in self.neighbors(cx, cy):
                        stone = self.board[ny][nx]
                        if stone == EMPTY and (nx, ny) not in visited:
                            stack.append((nx, ny))
                        elif stone != EMPTY:
                            bordering.add(stone)
                if len(bordering) == 1:
                    owner = next(iter(bordering))
                    territory[owner].update(region)
                else:
                    neutral.update(region)
        return territory, neutral

    def scoring_board(self):
        board = copy.deepcopy(self.board)
        dead_counts = {BLACK: 0, WHITE: 0}
        for x, y in self.marked_dead:
            if board[y][x] != EMPTY:
                dead_counts[board[y][x]] += 1
                board[y][x] = EMPTY
        return board, dead_counts

    def territory_map_for_board(self, board):
        visited = set()
        territory = {BLACK: set(), WHITE: set()}
        neutral = set()
        for y in range(self.size):
            for x in range(self.size):
                if board[y][x] != EMPTY or (x, y) in visited:
                    continue
                region = set()
                bordering = set()
                stack = [(x, y)]
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in visited:
                        continue
                    visited.add((cx, cy))
                    region.add((cx, cy))
                    for nx, ny in self.neighbors(cx, cy):
                        stone = board[ny][nx]
                        if stone == EMPTY and (nx, ny) not in visited:
                            stack.append((nx, ny))
                        elif stone != EMPTY:
                            bordering.add(stone)
                if len(bordering) == 1:
                    owner = next(iter(bordering))
                    territory[owner].update(region)
                else:
                    neutral.update(region)
        return territory, neutral

    def toggle_dead_group(self, x: int, y: int):
        if not self.scoring_mode:
            return False, "Dead stones can only be marked during scoring."
        if not self.on_board(x, y):
            return False, "Point is outside the board."
        if self.board[y][x] == EMPTY:
            return False, "Choose a stone group to mark as dead."

        self.push_undo_state()
        group, _ = self.group_and_liberties(x, y, self.board)
        if all(point in self.marked_dead for point in group):
            self.marked_dead.difference_update(group)
            return True, "Removed dead-stone mark from the group."
        self.marked_dead.update(group)
        return True, "Marked the group as dead."

    def resume_play(self):
        if not self.scoring_mode:
            return False, "Scoring is not active."
        self.push_undo_state()
        self.scoring_mode = False
        self.pass_count = 0
        self.marked_dead.clear()
        self.last_move = ("resume", self.turn)
        return True, "Resumed play from the scoring phase."

    def finalize_scoring(self):
        if not self.scoring_mode:
            return False, "Scoring is not active."
        self.push_undo_state()
        result = self.score()
        self.game_over = True
        self.scoring_mode = False
        self.winner = result["winner"]
        self.last_move = ("finalize", self.winner)
        return True, "Scoring finalized."

    def score(self):
        board_for_scoring, dead_counts = self.scoring_board()
        territory, neutral = self.territory_map_for_board(board_for_scoring)
        stones = {
            BLACK: sum(1 for row in board_for_scoring for stone in row if stone == BLACK),
            WHITE: sum(1 for row in board_for_scoring for stone in row if stone == WHITE),
        }
        adjusted_captures = {
            BLACK: self.captures[BLACK] + dead_counts[WHITE],
            WHITE: self.captures[WHITE] + dead_counts[BLACK],
        }
        if self.ruleset == "japanese":
            black_score = len(territory[BLACK]) + adjusted_captures[BLACK]
            white_score = len(territory[WHITE]) + adjusted_captures[WHITE] + self.komi
        else:
            black_score = stones[BLACK] + len(territory[BLACK])
            white_score = stones[WHITE] + len(territory[WHITE]) + self.komi

        if black_score > white_score:
            winner = BLACK
            margin = black_score - white_score
        else:
            winner = WHITE
            margin = white_score - black_score

        return {
            "winner": winner,
            "margin": margin,
            "black_score": black_score,
            "white_score": white_score,
            "black_territory": len(territory[BLACK]),
            "white_territory": len(territory[WHITE]),
            "territory": territory,
            "neutral": neutral,
            "stones": stones,
            "dead_counts": dead_counts,
            "captures": adjusted_captures,
            "scoring_board": board_for_scoring,
        }


class GoAI:
    def choose_move(self, game: GoGame):
        candidates = self._candidate_moves(game)
        if not candidates:
            return None

        if self._should_pass(game):
            return None

        depth = 3 if game.size <= 9 else 2
        width = 10 if game.size <= 9 else 8
        best_score = -10**9
        best_moves = []

        for x, y in candidates[:width]:
            child = copy.deepcopy(game)
            result = child.play_move(x, y)
            if not result.success:
                continue
            score = -self._search(child, depth - 1, -10**9, 10**9, game.turn)
            score += random.uniform(-0.08, 0.08)
            if score > best_score:
                best_score = score
                best_moves = [(x, y)]
            elif math.isclose(score, best_score, abs_tol=0.25):
                best_moves.append((x, y))

        if not best_moves:
            return None
        return random.choice(best_moves)

    def _search(self, game: GoGame, depth: int, alpha: float, beta: float, root_player: int):
        if depth == 0 or game.game_over or game.scoring_mode:
            return self._evaluate_position(game, root_player)

        candidates = self._candidate_moves(game)
        if not candidates:
            passed = copy.deepcopy(game)
            passed.pass_turn()
            if passed.scoring_mode:
                return self._evaluate_position(passed, root_player)
            return -self._search(passed, depth - 1, -beta, -alpha, root_player)

        value = -10**9
        for x, y in candidates:
            child = copy.deepcopy(game)
            result = child.play_move(x, y)
            if not result.success:
                continue
            score = -self._search(child, depth - 1, -beta, -alpha, root_player)
            value = max(value, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return value

    def _candidate_moves(self, game: GoGame):
        legal = game.legal_moves()
        if not legal:
            return []

        occupied = {(x, y) for y in range(game.size) for x in range(game.size) if game.board[y][x] != EMPTY}
        if not occupied:
            center = game.size // 2
            opening = []
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    x, y = center + dx, center + dy
                    if game.on_board(x, y):
                        is_legal, _ = game.is_legal_move(x, y)
                        if is_legal:
                            opening.append((x, y))
            return opening or [(x, y) for x, y, _, _ in legal]

        neighborhood = set()
        for ox, oy in occupied:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    nx, ny = ox + dx, oy + dy
                    if game.on_board(nx, ny):
                        neighborhood.add((nx, ny))

        ranked = []
        for x, y, captured, board_after in legal:
            if (x, y) not in neighborhood and game.move_number > 8:
                continue
            ranked.append((self._move_heuristic(game, x, y, captured, board_after), x, y))

        if not ranked:
            ranked = [
                (self._move_heuristic(game, x, y, captured, board_after), x, y)
                for x, y, captured, board_after in legal
            ]

        ranked.sort(reverse=True)
        return [(x, y) for _, x, y in ranked[:18]]

    def _move_heuristic(self, game: GoGame, x: int, y: int, captured: int, board_after):
        center = (game.size - 1) / 2
        group, liberties = game.group_and_liberties(x, y, board_after)
        distance = abs(x - center) + abs(y - center)
        local_empty = sum(1 for nx, ny in game.neighbors(x, y) if board_after[ny][nx] == EMPTY)
        friendly_adjacent = sum(1 for nx, ny in game.neighbors(x, y) if game.board[ny][nx] == game.turn)
        enemy_adjacent = sum(1 for nx, ny in game.neighbors(x, y) if game.board[ny][nx] == opponent(game.turn))

        influence = 0.0
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                nx, ny = x + dx, y + dy
                if not game.on_board(nx, ny):
                    continue
                stone = game.board[ny][nx]
                weight = 1.0 / (abs(dx) + abs(dy) + 1)
                if stone == game.turn:
                    influence += weight
                elif stone == opponent(game.turn):
                    influence -= weight

        score = 0.0
        score += captured * 22
        score += len(liberties) * 2.8
        score += local_empty * 1.2
        score += friendly_adjacent * 1.4
        score += enemy_adjacent * 2.2
        score += influence * 1.5
        score -= distance * 0.32

        if len(group) == 1 and len(liberties) <= 1:
            score -= 18
        elif len(liberties) == 2:
            score -= 4

        return score

    def _evaluate_position(self, game: GoGame, root_player: int):
        score_data = game.score()
        score_delta = score_data["black_score"] - score_data["white_score"]
        if root_player == WHITE:
            score_delta = -score_delta

        territory_delta = score_data["black_territory"] - score_data["white_territory"]
        if root_player == WHITE:
            territory_delta = -territory_delta

        liberties_delta = 0
        stones_delta = 0
        for y in range(game.size):
            for x in range(game.size):
                stone = game.board[y][x]
                if stone == EMPTY:
                    continue
                _, liberties = game.group_and_liberties(x, y)
                sign = 1 if stone == root_player else -1
                liberties_delta += min(len(liberties), 4) * sign
                stones_delta += sign

        if game.game_over:
            score_delta += 1000 if game.winner == root_player else -1000

        return score_delta * 12 + liberties_delta * 1.4 + stones_delta * 0.8 + territory_delta * 0.5

    def _should_pass(self, game: GoGame):
        if game.move_number < game.size:
            return False
        score = game.score()
        score_delta = score["black_score"] - score["white_score"]
        if game.turn == WHITE:
            score_delta = -score_delta
        return score_delta > 8 and game.pass_count >= 1
