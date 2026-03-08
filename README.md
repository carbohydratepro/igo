# Local Go Arena

Flask ベースでローカル動作する囲碁アプリです。ブラウザ上で対局できます。

## 機能

- 9路盤 / 13路盤 / 19路盤
- 一人モード（CPU） / 二人モード
- 日本ルール / 中国ルール
- 黒番 / 白番の選択
- コウ、打ち上げ、自殺手禁止
- パス、投了、待った
- 連続 2 パスで終局、簡易採点

## 構成

- `app.py`: Flask サーバー
- `go_engine.py`: 囲碁ルールと CPU
- `templates/index.html`: 画面
- `static/app.js`: 盤面描画と操作
- `static/styles.css`: UI スタイル
- `.venv/`: このプロジェクト用の仮想環境ディレクトリ

## venv 構築

この環境では Linux 側の `python3` が未配置だったため、Windows 側の Python 3.13 を使って `.venv` を作成しています。

```bash
'/mnt/c/Users/masas/AppData/Local/Programs/Python/Python313/python.exe' -m venv .venv
'/mnt/c/Users/masas/AppData/Local/Programs/Python/Python313/python.exe' -m pip install Flask --target '/home/igo/.venv/Lib/site-packages'
```

## 起動方法

```bash
bash run.sh
```

起動後にブラウザで `http://127.0.0.1:5000` を開いてください。

## 補足

- `Flask` は `.venv/Lib/site-packages` を `app.py` 側で読み込むようにしています。
- 採点は盤面ベースの簡易実装です。死活判定の手動確定やセキ精算は未対応です。
- CPU はローカル動作向けの軽量ヒューリスティックです。
