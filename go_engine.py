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
        self.game_over = False
        self.winner = None
        self.last_move = None
        self.resigned_player = None
        self.move_number = 0
        self.board_history = [self.board_hash()]
        self.state_stack = []

    def clone_state(self):
        return {
            "board": copy.deepcopy(self.board),
            "turn": self.turn,
            "captures": dict(self.captures),
            "pass_count": self.pass_count,
            "game_over": self.game_over,
            "winner": self.winner,
            "last_move": self.last_move,
            "resigned_player": self.resigned_player,
            "move_number": self.move_number,
            "board_history": list(self.board_history),
        }

    def restore_state(self, state) -> None:
        self.board = copy.deepcopy(state["board"])
        self.turn = state["turn"]
        self.captures = dict(state["captures"])
        self.pass_count = state["pass_count"]
        self.game_over = state["game_over"]
        self.winner = state["winner"]
        self.last_move = state["last_move"]
        self.resigned_player = state["resigned_player"]
        self.move_number = state["move_number"]
        self.board_history = list(state["board_history"])

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
        self.push_undo_state()
        current = self.turn
        self.pass_count += 1
        self.last_move = ("pass", current)
        self.move_number += 1
        self.board_history.append(self.board_hash())
        self.turn = opponent(self.turn)
        if self.pass_count >= 2:
            self.game_over = True
            return MoveResult(True, game_over=True)
        return MoveResult(True)

    def resign(self) -> None:
        if self.game_over:
            return
        self.push_undo_state()
        self.resigned_player = self.turn
        self.winner = opponent(self.turn)
        self.game_over = True

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

    def score(self):
        territory, neutral = self.territory_map()
        stones = {
            BLACK: sum(1 for row in self.board for stone in row if stone == BLACK),
            WHITE: sum(1 for row in self.board for stone in row if stone == WHITE),
        }
        if self.ruleset == "japanese":
            black_score = len(territory[BLACK]) + self.captures[BLACK]
            white_score = len(territory[WHITE]) + self.captures[WHITE] + self.komi
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
            "territory": territory,
            "neutral": neutral,
            "stones": stones,
        }


class GoAI:
    def choose_move(self, game: GoGame):
        moves = game.legal_moves()
        if not moves:
            return None

        best_score = -10**9
        best_moves = []
        center = (game.size - 1) / 2

        for x, y, captured, board_after in moves:
            score = 0.0
            distance = abs(x - center) + abs(y - center)
            group, liberties = game.group_and_liberties(x, y, board_after)
            local_empty = sum(1 for nx, ny in game.neighbors(x, y) if board_after[ny][nx] == EMPTY)
            friendly_adjacent = sum(1 for nx, ny in game.neighbors(x, y) if game.board[ny][nx] == game.turn)
            enemy_adjacent = sum(1 for nx, ny in game.neighbors(x, y) if game.board[ny][nx] == opponent(game.turn))

            score += captured * 20
            score += len(liberties) * 2.5
            score += local_empty * 1.2
            score += friendly_adjacent * 0.8
            score += enemy_adjacent * 1.1
            score -= distance * 0.45

            if len(group) == 1 and len(liberties) <= 1:
                score -= 12

            if score > best_score:
                best_score = score
                best_moves = [(x, y)]
            elif math.isclose(score, best_score, abs_tol=0.5):
                best_moves.append((x, y))

        if best_score < 0.5 and game.move_number > game.size:
            return None
        return random.choice(best_moves)
