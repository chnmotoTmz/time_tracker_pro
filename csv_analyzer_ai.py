import os
import logging
import pandas as pd
import json
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
import re
from dateutil import parser

# 環境変数の読み込み
load_dotenv()

# ロギング設定
logger = logging.getLogger(__name__)

class GeminiCSVAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model = genai.GenerativeModel('gemini-pro')

    def analyze_csv_structure(self, file_path):
        """CSVファイルの構造を解析"""
        try:
            df = pd.read_csv(file_path, nrows=0)  # ヘッダーのみ読み込み
            headers = df.columns.tolist()
            return self._analyze_with_gemini(headers)
        except Exception as e:
            self.logger.error(f"CSVファイル解析エラー: {str(e)}")
            return None

    def _analyze_with_gemini(self, headers):
        """Gemini APIを使用してヘッダーを分析"""
        try:
            prompt = f"""
            以下のCSVヘッダーから、タスク名、開始日、終了日、進捗率を表すカラムを特定してください：
            {headers}
            
            以下の形式でJSON形式で返答してください：
            {{
                "task_name": "タスク名のカラム",
                "start_date": "開始日のカラム",
                "end_date": "終了日のカラム",
                "progress": "進捗率のカラム（オプション）"
            }}
            """
            
            response = self.model.generate_content(prompt)
            mapping = eval(response.text)  # 注意: 実際の実装ではJSONパースを使用すべき
            
            return mapping if self._validate_mapping(mapping) else None
            
        except Exception as e:
            self.logger.error(f"Gemini API エラー: {str(e)}")
            return None

    def _validate_mapping(self, mapping):
        """必須カラムが存在するか確認"""
        required_columns = ['task_name', 'start_date', 'end_date']
        return all(col in mapping for col in required_columns)

    def validate_and_transform_data(self, df, mapping):
        """データの検証と変換"""
        try:
            tasks = []
            for _, row in df.iterrows():
                task = {
                    'name': row[mapping['task_name']],
                    'start_date': self.guess_date_format(row[mapping['start_date']]),
                    'end_date': self.guess_date_format(row[mapping['end_date']]),
                    'progress': self.convert_progress(row.get(mapping.get('progress', ''), 0))
                }
                
                if all(task.values()):  # すべての値が有効な場合のみ追加
                    tasks.append(task)
                else:
                    self.logger.warning(f"無効なタスクデータ: {task}")
            
            return tasks
        except Exception as e:
            self.logger.error(f"データ変換エラー: {str(e)}")
            return None

    def guess_date_format(self, date_str):
        """日付文字列のフォーマットを推測"""
        try:
            parsed_date = parser.parse(str(date_str))
            return parsed_date.strftime('%Y-%m-%d')
        except:
            return None

    def convert_progress(self, progress_str):
        """進捗値を標準形式（0-100の整数）に変換"""
        try:
            # 数値とパーセント記号を抽出
            number = re.search(r'(\d+\.?\d*)', str(progress_str))
            if number:
                value = float(number.group(1))
                # パーセント記号がない場合は1以下なら100倍
                if '%' not in str(progress_str) and value <= 1:
                    value *= 100
                return int(min(100, max(0, value)))
        except:
            pass
        return 0

    def analyze_and_convert(self, file_path):
        """CSVファイルを解析して変換"""
        try:
            # 構造を解析
            mapping = self.analyze_csv_structure(file_path)
            if not mapping:
                raise ValueError("CSVの構造を解析できませんでした")
            
            # データを変換
            result = self.validate_and_transform_data(pd.read_csv(file_path), mapping)
            if not result:
                raise ValueError("データの変換に失敗しました")
            
            return result, mapping
            
        except Exception as e:
            logger.error(f"CSV解析中にエラーが発生しました: {str(e)}")
            return None, None 