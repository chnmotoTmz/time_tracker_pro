import json
import logging
import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai
from dotenv import load_dotenv
import re
import uuid
import os

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('gantt_app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Gemini APIの設定
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-pro-exp-02-05')

class BaseAgent:
    """すべてのエージェントの基底クラス"""
    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger(name)
        self.model = model
        self.created_at = datetime.now()
        self.request_count = 0
        self.success_count = 0
        self.request_history = {}  # 環境適応のためのリクエスト履歴

    def log_request(self, request):
        """リクエストを記録し、パターンを学習"""
        self.request_count += 1
        # リクエストパターンを抽出（単純な例として最初の2単語を使用）
        pattern = ' '.join(request.lower().split()[:2])
        self.request_history[pattern] = self.request_history.get(pattern, 0) + 1

    def get_top_patterns(self, limit=3):
        """最も頻繁に使用されるリクエストパターンを取得"""
        if not self.request_history:
            return []
        sorted_patterns = sorted(self.request_history.items(), key=lambda x: x[1], reverse=True)
        return sorted_patterns[:limit]

    def is_adaptable(self):
        """エージェントが適応可能かどうかを判断（リクエスト数が一定以上）"""
        return self.request_count >= 10

class TaskAgent(BaseAgent):
    """タスク管理を担当するエージェント（進化機能を含む）"""
    def __init__(self):
        super().__init__("TaskAgent")
        self.task_schema = {
            "id": "string(uuid)",
            "name": "string",
            "start_date": "string(ISO date)",
            "end_date": "string(ISO date)",
            "progress": "number(0-100)",
            "status": "string(created|in_progress|completed)",
            "dependencies": "array of task ids",
            "metadata": {
                "created_at": "string(ISO date)",
                "updated_at": "string(ISO date)",
                "duration": "number",
                "original_data": "object"
            }
        }

    def validate_tasks(self, tasks):
        """タスクのバリデーション"""
        valid_tasks = []
        for task in tasks:
            # 最低限必要な項目の確認
            if 'name' not in task or not task['name']:
                self.logger.warning(f"タスク名が設定されていません: {task}")
                continue
                
            # IDの確認（なければ生成）
            if 'id' not in task:
                task['id'] = str(uuid.uuid4())
                
            # 日付の確認
            if 'start_date' not in task:
                task['start_date'] = datetime.now().isoformat()
            if 'end_date' not in task:
                # 開始日から1日後をデフォルトに
                start = datetime.fromisoformat(task['start_date'].split('T')[0])
                task['end_date'] = (start + timedelta(days=1)).isoformat()
                
            # ステータスと進捗率の確認
            if 'status' not in task:
                task['status'] = 'created'
            if 'progress' not in task:
                task['progress'] = 0
                
            # 依存関係の確認
            if 'dependencies' not in task:
                task['dependencies'] = []
                
            # メタデータの確認
            if 'metadata' not in task:
                task['metadata'] = {}
            if 'created_at' not in task['metadata']:
                task['metadata']['created_at'] = datetime.now().isoformat()
            if 'updated_at' not in task['metadata']:
                task['metadata']['updated_at'] = datetime.now().isoformat()
                
            valid_tasks.append(task)
            
        return valid_tasks

    def create_task(self, name, start_date=None, duration=1):
        """タスクの作成"""
        if not start_date:
            start_date = datetime.now()
        elif isinstance(start_date, str):
            try:
                start_date = datetime.fromisoformat(start_date.split('T')[0])
            except ValueError:
                start_date = datetime.now()
                
        end_date = start_date + timedelta(days=duration)
        
        task = {
            'id': str(uuid.uuid4()),
            'name': name,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'progress': 0,
            'status': 'created',
            'dependencies': [],
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'duration': duration
            }
        }
        
        self.logger.info(f"タスクを作成しました: {name}")
        return task

    def update_task_status(self, task, new_status):
        """タスクのステータス更新"""
        valid_statuses = ['created', 'in_progress', 'completed']
        if new_status not in valid_statuses:
            self.logger.error(f"無効なステータス: {new_status}")
            return task
            
        old_status = task['status']
        task['status'] = new_status
        task['metadata']['updated_at'] = datetime.now().isoformat()
        
        # 完了時は進捗率を100%に
        if new_status == 'completed':
            task['progress'] = 100
            
        self.logger.info(f"タスクのステータスを更新しました: {task['name']} ({old_status} -> {new_status})")
        return task

    def set_dependency(self, task, dependency_task):
        """依存関係の設定（進化機能）"""
        if dependency_task['id'] not in task['dependencies']:
            task['dependencies'].append(dependency_task['id'])
            task['metadata']['updated_at'] = datetime.now().isoformat()
            self.logger.info(f"依存関係を設定しました: {task['name']} -> {dependency_task['name']}")
        return task

    def extract_task_info(self, text):
        """自然言語テキストからタスク情報を抽出"""
        try:
            prompt = f"""
            以下のテキストからタスク情報を抽出し、JSONとして返してください:
            
            テキスト: {text}
            
            抽出する情報:
            - タスク名
            - 開始日（言及されていれば）
            - 期間（日数、言及されていれば）
            - 依存関係（「〜に依存」という形で言及されていれば）
            
            JSON形式:
            {{
                "name": "タスク名",
                "start_date": "YYYY-MM-DD",
                "duration": 1,
                "depends_on": "依存先タスク名"
            }}
            """
            
            response = self.model.generate_content(prompt)
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                info = json.loads(json_match.group())
                return info
            return None
        except Exception as e:
            self.logger.error(f"タスク情報の抽出に失敗: {str(e)}")
            return None

    def process_tasks(self, tasks):
        """タスクリストの処理"""
        return self.validate_tasks(tasks)

    def process_input(self, text, current_tasks=[]):
        """自然言語入力からタスク処理"""
        self.log_request(text)  # 環境適応のためのリクエスト記録
        
        task_info = self.extract_task_info(text)
        if not task_info:
            return {
                'status': 'error',
                'message': 'タスク情報を抽出できませんでした'
            }
            
        # タスク作成
        if 'name' in task_info:
            start_date = task_info.get('start_date', datetime.now().isoformat())
            duration = int(task_info.get('duration', 1))
            new_task = self.create_task(task_info['name'], start_date, duration)
            
            # 依存関係の処理
            if 'depends_on' in task_info and task_info['depends_on']:
                for task in current_tasks:
                    if task['name'].lower() == task_info['depends_on'].lower():
                        new_task = self.set_dependency(new_task, task)
                        break
            
            return {
                'status': 'success',
                'message': f"タスク「{new_task['name']}」を作成しました",
                'task': new_task
            }
            
        return {
            'status': 'error',
            'message': 'タスク名が指定されていません'
        }

    def suggest_optimizations(self, tasks):
        """タスクの最適化提案（環境適応）"""
        if not self.is_adaptable() or not tasks:
            return None
            
        # 頻繁に使用されるパターンに基づくアクション
        top_patterns = self.get_top_patterns()
        suggestions = []
        
        for pattern, count in top_patterns:
            if pattern.startswith("create") and count >= 5:
                suggestions.append({
                    "type": "suggestion",
                    "message": "タスク作成が頻繁に行われています。テンプレートの導入を検討してください。"
                })
            elif pattern.startswith("set depend") and count >= 3:
                suggestions.append({
                    "type": "suggestion",
                    "message": "依存関係の設定が頻繁に行われています。依存関係図の表示機能を追加してみてはいかがですか？"
                })
                
        return suggestions if suggestions else None

class ChartAgent(BaseAgent):
    """チャート表示を担当するエージェント"""
    def __init__(self):
        super().__init__("ChartAgent")
        # デフォルト設定
        self.default_settings = {
            "colors": {
                "created": "lightgray",
                "in_progress": "lightblue",
                "completed": "lightgreen"
            },
            "display": {
                "show_dependencies": True,
                "show_progress": True,
                "view_mode": "days"  # days, weeks, months
            }
        }
        self.current_settings = self.default_settings.copy()
        
    def process_settings(self, settings):
        """チャート設定の処理"""
        self.log_request(f"update settings: {settings}")  # 環境適応のためのリクエスト記録
        
        # 設定の更新
        if 'colors' in settings:
            self.current_settings['colors'].update(settings['colors'])
        if 'display' in settings:
            self.current_settings['display'].update(settings['display'])
            
        return self.current_settings
        
    def process_input(self, text, current_tasks=[]):
        """自然言語入力からチャート設定を更新"""
        self.log_request(text)  # 環境適応のためのリクエスト記録
        
        try:
            prompt = f"""
            以下のテキストからチャート表示設定を抽出し、JSONとして返してください:
            
            テキスト: {text}
            
            抽出する情報:
            - 色の変更（ステータスごとの色指定）
            - 表示モード変更（日/週/月表示）
            - 依存関係表示（表示/非表示）
            - 進捗表示（表示/非表示）
            
            JSON形式:
            {{
                "colors": {{
                    "created": "色名",
                    "in_progress": "色名",
                    "completed": "色名"
                }},
                "display": {{
                    "show_dependencies": true/false,
                    "show_progress": true/false,
                    "view_mode": "days/weeks/months"
                }}
            }}
            """
            
            response = self.model.generate_content(prompt)
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                settings = json.loads(json_match.group())
                # 設定を更新
                return {
                    'status': 'success',
                    'message': 'チャート設定を更新しました',
                    'settings': self.process_settings(settings)
                }
            
            return {
                'status': 'error',
                'message': '設定情報を抽出できませんでした'
            }
            
        except Exception as e:
            self.logger.error(f"設定情報の抽出に失敗: {str(e)}")
            return {
                'status': 'error',
                'message': f'設定の処理中にエラーが発生しました: {str(e)}'
            }

    def suggest_improvements(self):
        """チャート表示の改善提案（環境適応）"""
        if not self.is_adaptable():
            return None
            
        # 頻繁に使用されるパターンに基づくアクション
        top_patterns = self.get_top_patterns()
        suggestions = []
        
        for pattern, count in top_patterns:
            if pattern.startswith("change color") and count >= 3:
                suggestions.append({
                    "type": "suggestion",
                    "message": "色の変更が頻繁に行われています。カラーパレットの追加を検討してください。"
                })
            elif pattern.startswith("change view") and count >= 3:
                suggestions.append({
                    "type": "suggestion",
                    "message": "表示モードの切り替えが頻繁に行われています。ビュー切替ボタンを目立たせることを検討してください。"
                })
                
        return suggestions if suggestions else None

class DialogueAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 進捗更新の表現パターンを修正
        self.progress_patterns = [
            r'進捗[をにが](\d+)[%％]',
            r'進捗率[をにが](\d+)',
            r'(\d+)[%％][にまで]',
            r'完了率[をにが](\d+)',
            r'進捗状況[をにが](\d+)',
            r'(\d+)[%％]に[設定更新]'
        ]

    def process_input(self, user_input, tasks):
        try:
            # 複数コマンドの処理
            if '\n' in user_input:
                commands = [cmd.strip() for cmd in user_input.split('\n') if cmd.strip()]
                return self._process_multiple_commands(commands, tasks)

            # 単一コマンドの処理
            return self._process_single_command(user_input, tasks)
                
        except Exception as e:
            self.logger.error(f"対話処理中にエラー: {str(e)}")
            return {
                'action': 'none',
                'message': f'エラーが発生しました: {str(e)}'
            }

    def _process_multiple_commands(self, commands, tasks):
        """複数コマンドを順次処理"""
        current_tasks = tasks.copy()
        results = []
        
        for command in commands:
            result = self._process_single_command(command, current_tasks)
            if result['action'] == 'update_tasks':
                current_tasks = result['tasks']
                results.append(result['message'])
        
        if results:
            return {
                'action': 'update_tasks',
                'tasks': current_tasks,
                'message': '\n'.join(results)
            }
        return {'action': 'none', 'message': 'コマンドを認識できませんでした'}

    def _process_single_command(self, command, tasks):
        """単一コマンドの処理"""
        # タスク名の抽出
        task_name = None
        for task in tasks:
            if task['name'] in command:
                task_name = task['name']
                break

        if not task_name:
            return {'action': 'none', 'message': 'タスクが見つかりませんでした'}

        # 進捗率の抽出
        progress = None
        for pattern in self.progress_patterns:
            match = re.search(pattern, command)
            if match:
                progress = int(match.group(1))
                if not (0 <= progress <= 100):
                    return {'action': 'none', 'message': '進捗率は0-100の範囲で指定してください'}
                break

        # コマンドの種類を判断して処理
        if "完了" in command and not progress:
            return self._update_task_status(tasks, task_name, 'completed', 100)
        elif "開始" in command:
            return self._update_task_status(tasks, task_name, 'in_progress')
        elif progress is not None:
            return self._update_task_progress(tasks, task_name, progress)

        return {'action': 'none', 'message': 'コマンドを認識できませんでした'}

    def _update_task_status(self, tasks, task_name, status, progress=None):
        updated_tasks = []
        for task in tasks:
            new_task = task.copy()
            if task['name'] == task_name:
                new_task['status'] = status
                if progress is not None:
                    new_task['progress'] = progress
            updated_tasks.append(new_task)
        
        return {
            'action': 'update_tasks',
            'tasks': updated_tasks,
            'message': f'{task_name}のステータスを{status}に更新しました'
        }

    def _update_task_progress(self, tasks, task_name, progress):
        updated_tasks = []
        for task in tasks:
            new_task = task.copy()
            if task['name'] == task_name:
                new_task['progress'] = progress
                new_task['status'] = 'completed' if progress == 100 else 'in_progress'
            updated_tasks.append(new_task)
        
        return {
            'action': 'update_tasks',
            'tasks': updated_tasks,
            'message': f'{task_name}の進捗を{progress}%に更新しました'
        }
