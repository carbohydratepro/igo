import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SITE_PACKAGES = BASE_DIR / ".venv" / "Lib" / "site-packages"
if SITE_PACKAGES.exists():
    sys.path.insert(0, str(SITE_PACKAGES))

from flask import Flask, jsonify, render_template, request

from go_engine import BLACK, WHITE, GoAI, GoGame, player_name, rules_name


app = Flask(__name__)


class GameSession:
    def __init__(self):
        self.ai = GoAI()
        self.new_game()

    def new_game(self, size=19, ruleset="japanese", komi=6.5, mode="cpu", human_color=BLACK):
        self.game = GoGame(size=size, ruleset=ruleset, komi=komi)
        self.mode = mode
        self.human_color = human_color
        self.message = "New game started."
        if self.mode == "cpu" and self.game.turn != self.human_color:
            self.maybe_cpu_turn()

    def is_cpu_turn(self):
        return self.mode == "cpu" and not self.game.game_over and self.game.turn != self.human_color

    def maybe_cpu_turn(self):
        if not self.is_cpu_turn():
            return
        move = self.ai.choose_move(self.game)
        if move is None:
            result = self.game.pass_turn()
            self.message = "CPU passed."
            if result.success and self.game.scoring_mode:
                self.message = "Both players passed. Mark dead stones, then finalize scoring."
        else:
            x, y = move
            result = self.game.play_move(x, y)
            self.message = f"CPU played at {x + 1}, {y + 1}."
            if result.captured:
                self.message += f" Captured {result.captured} stone(s)."

    def apply_move(self, x, y):
        if self.game.scoring_mode:
            ok, message = self.game.toggle_dead_group(x, y)
            self.message = message
            return ok, message
        if self.is_cpu_turn():
            return False, "It is currently the CPU's turn."
        result = self.game.play_move(x, y)
        if not result.success:
            return False, result.reason
        self.message = f"{player_name(-self.game.turn)} played at {x + 1}, {y + 1}."
        if result.captured:
            self.message += f" Captured {result.captured} stone(s)."
        if self.game.scoring_mode:
            self.message = "Both players passed. Mark dead stones, then finalize scoring."
        elif not self.game.game_over:
            self.maybe_cpu_turn()
        return True, self.message

    def pass_turn(self):
        if self.game.scoring_mode:
            return False, "Scoring is active. Finalize scoring or resume play."
        if self.is_cpu_turn():
            return False, "It is currently the CPU's turn."
        result = self.game.pass_turn()
        if not result.success:
            return False, result.reason
        self.message = f"{player_name(-self.game.turn)} passed."
        if self.game.scoring_mode:
            self.message = "Both players passed. Mark dead stones, then finalize scoring."
        elif not self.game.game_over:
            self.maybe_cpu_turn()
        return True, self.message

    def resign(self):
        if self.game.scoring_mode:
            return False, "Scoring is active. Finalize scoring or resume play."
        if self.is_cpu_turn():
            return False, "It is currently the CPU's turn."
        self.game.resign()
        self.message = f"{player_name(self.game.winner)} wins by resignation."
        return True, self.message

    def undo(self):
        steps = 2 if self.mode == "cpu" and len(self.game.state_stack) >= 2 else 1
        if not self.game.undo(steps=steps):
            return False, "Nothing to undo."
        self.message = "Undid the previous move."
        return True, self.message

    def finalize_scoring(self):
        ok, message = self.game.finalize_scoring()
        self.message = message
        return ok, message

    def resume_play(self):
        ok, message = self.game.resume_play()
        self.message = message
        return ok, message

    def state_payload(self):
        score = self.game.score()
        if self.game.game_over:
            if self.game.resigned_player is not None:
                headline = f"{player_name(self.game.winner)} wins by resignation."
            else:
                headline = (
                    f"{player_name(score['winner'])} wins by {score['margin']:.1f}. "
                    f"Black {score['black_score']:.1f} - White {score['white_score']:.1f}"
                )
        elif self.game.scoring_mode:
            headline = "Scoring phase"
        else:
            headline = f"{player_name(self.game.turn)} to play"
            if self.is_cpu_turn():
                headline += " (CPU)"

        return {
            "board": self.game.board,
            "size": self.game.size,
            "turn": self.game.turn,
            "captures": self.game.captures,
            "move_number": self.game.move_number,
            "pass_count": self.game.pass_count,
            "scoring_mode": self.game.scoring_mode,
            "game_over": self.game.game_over,
            "winner": self.game.winner,
            "last_move": self.game.last_move,
            "marked_dead": sorted([list(point) for point in self.game.marked_dead]),
            "ruleset": self.game.ruleset,
            "rules_label": rules_name(self.game.ruleset),
            "komi": self.game.komi,
            "mode": self.mode,
            "human_color": self.human_color,
            "headline": headline,
            "message": self.message,
            "score": {
                "winner": score["winner"],
                "margin": score["margin"],
                "black_score": score["black_score"],
                "white_score": score["white_score"],
                "black_stones": score["stones"][BLACK],
                "white_stones": score["stones"][WHITE],
                "black_territory": len(score["territory"][BLACK]),
                "white_territory": len(score["territory"][WHITE]),
                "neutral_points": len(score["neutral"]),
                "dead_black": score["dead_counts"][BLACK],
                "dead_white": score["dead_counts"][WHITE],
                "captures_black": score["captures"][BLACK],
                "captures_white": score["captures"][WHITE],
            },
        }


session = GameSession()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def state():
    return jsonify(session.state_payload())


@app.post("/api/new-game")
def new_game():
    payload = request.get_json(force=True)
    size = int(payload.get("size", 19))
    ruleset = payload.get("ruleset", "japanese")
    mode = payload.get("mode", "cpu")
    human_color = int(payload.get("human_color", BLACK))
    komi = float(payload.get("komi", 6.5))
    session.new_game(size=size, ruleset=ruleset, komi=komi, mode=mode, human_color=human_color)
    return jsonify(session.state_payload())


@app.post("/api/play")
def play():
    payload = request.get_json(force=True)
    ok, message = session.apply_move(int(payload["x"]), int(payload["y"]))
    state = session.state_payload()
    state["ok"] = ok
    state["message"] = message
    return jsonify(state), 200 if ok else 400


@app.post("/api/pass")
def pass_turn():
    ok, message = session.pass_turn()
    state = session.state_payload()
    state["ok"] = ok
    state["message"] = message
    return jsonify(state), 200 if ok else 400


@app.post("/api/resign")
def resign():
    ok, message = session.resign()
    state = session.state_payload()
    state["ok"] = ok
    state["message"] = message
    return jsonify(state), 200 if ok else 400


@app.post("/api/undo")
def undo():
    ok, message = session.undo()
    state = session.state_payload()
    state["ok"] = ok
    state["message"] = message
    return jsonify(state), 200 if ok else 400


@app.post("/api/finalize-scoring")
def finalize_scoring():
    ok, message = session.finalize_scoring()
    state = session.state_payload()
    state["ok"] = ok
    state["message"] = message
    return jsonify(state), 200 if ok else 400


@app.post("/api/resume-play")
def resume_play():
    ok, message = session.resume_play()
    state = session.state_payload()
    state["ok"] = ok
    state["message"] = message
    return jsonify(state), 200 if ok else 400


if __name__ == "__main__":
    host = os.environ.get("GO_APP_HOST", "127.0.0.1")
    port = int(os.environ.get("GO_APP_PORT", "5000"))
    app.run(host=host, port=port, debug=False)
