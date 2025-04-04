# ガントチャートアプリケーション

## 概要
CSVファイルからタスク情報を読み込み、ガントチャートとして視覚化するPythonアプリケーションです。

## 機能
- CSVファイルのインポート
- タスク情報の自動解析
- ガントチャートの表示
- タスクの期間と進捗の視覚化

## 必要要件
- Python 3.8以上
- 必要なパッケージ:
  - pandas
  - tkinter (通常はPythonに同梱)
  - python-dotenv
  - google-generativeai

## インストール方法
1. リポジトリをクローンまたはダウンロード
2. 必要なパッケージをインストール:
```bash
pip install -r requirements.txt
```
3. `.env`ファイルを作成し、Gemini APIキーを設定: 
```

## ファイル構造

```
gantt_app_tk.py      # メインアプリケーション
├── CSVAnalyzer      # CSVファイル解析クラス
├── GanttCanvas      # ガントチャート描画クラス
├── TaskEditor       # タスク編集クラス
└── GanttChart       # メインアプリケーションクラス
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグ報告や機能要望は、Issueとして報告してください。