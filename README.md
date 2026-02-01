<p align="center">
  <img src="docs/logo.png" alt="SnapLabel" width="300px">
</p>

<p align="center">
  <strong>軽量・高速な画像ラベリングツール</strong>
</p>

<p align="center">
  <a href="#機能">機能</a> •
  <a href="#起動方法">起動方法</a> •
  <a href="#使い方">使い方</a> •
  <a href="#キーボードショートカット">ショートカット</a> •
  <a href="#api">API</a>
</p>

---

<p align="center">
  <img src="docs/display.png" width="700px" alt="Screenshot">
</p>

## 機能

| 機能 | 説明 |
|------|------|
| 画像表示 | ディレクトリ内の画像（jpg/png）を順番に表示 |
| ラベル付け | OK/NGボタンまたはキーボードで素早くラベル付け |
| 履歴保持 | 再スキャン時もラベル済み画像の情報を維持 |
| 自動スキップ | ラベル付け済みの画像は自動でスキップ |
| 修正機能 | 前の画像に戻って修正可能 |
| エクスポート | CSVで結果をダウンロード |
| 進捗表示 | 総数・OK数・NG数・残数をリアルタイム表示 |

## 起動方法

```bash
# リポジトリをクローン
git clone https://github.com/hisashi-ito/SnapLabel.git
cd SnapLabel

# 画像を入れるディレクトリを作成
mkdir -p data

# 起動
docker-compose up --build
```

ブラウザで http://localhost:8000 にアクセス

## 使い方

1. ラベル付けしたい画像を `data/` ディレクトリに配置
2. ブラウザで `/data` と入力して「Scan」をクリック
3. OK/NGボタンでラベル付け（自動で次へ進む）
4. 完了したら「Export CSV」でダウンロード

### 作業の再開

作業履歴はデータベースに保存されます。同じディレクトリを再スキャンすると：
- ラベル付け済みの画像はスキップされ、未ラベルの画像のみ表示
- 新しく追加された画像も自動で検出

## キーボードショートカット

| キー | 動作 |
|:----:|------|
| `O` | OK |
| `N` | NG |
| `←` | 前の画像 |
| `→` | 次の画像 |

## API

| Method | Endpoint | 説明 |
|--------|----------|------|
| POST | `/scan` | ディレクトリをスキャン |
| GET | `/images/current` | 現在の画像を取得 |
| GET | `/images/next` | 次の画像へ |
| GET | `/images/prev` | 前の画像へ |
| POST | `/images/{id}/label` | ラベルを保存 |
| GET | `/stats` | 進捗状況を取得 |
| GET | `/export/csv` | CSVエクスポート |

## ディレクトリ構成

```
SnapLabel/
├── main.py              # FastAPIアプリケーション
├── database.py          # DB操作
├── requirements.txt     # 依存パッケージ
├── Dockerfile
├── docker-compose.yml
├── templates/
│   └── index.html       # フロントエンド
├── static/
│   └── style.css        # スタイル
├── data/                # 画像を配置するディレクトリ
└── db/                  # SQLiteデータベース（自動生成）
```

## 停止

```bash
docker-compose down
```

## 技術スタック

<p>
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" alt="Docker">
</p>

## License

MIT License
