import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import logging
import sys
import re
import uuid
from datetime import datetime, timedelta
from tkcalendar import DateEntry
from csv_analyzer_ai import GeminiCSVAnalyzer
from agents import TaskAgent, ChartAgent, DialogueAgent
from dateutil import parser

# ロギングの設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('gantt_app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class GanttCanvas(tk.Canvas):
    def __init__(self, master, tasks=None, **kwargs):
        super().__init__(master, **kwargs)
        self.tasks = tasks or []
        self.cell_width = 30
        self.row_height = 30
        self.header_height = 50
        self.task_width = 200
        self.bind('<Configure>', self.on_resize)
    
    def on_resize(self, event):
        self.redraw()
    
    def redraw(self):
        self.delete('all')
        if not self.tasks:
            return
        
        # 日付の範囲を計算
        start_date = min(datetime.datetime.strptime(task['start'], '%Y-%m-%d') for task in self.tasks)
        end_date = max(datetime.datetime.strptime(task['end'], '%Y-%m-%d') for task in self.tasks)
        days = (end_date - start_date).days + 1
        
        # キャンバスのサイズを設定
        total_width = self.task_width + (days * self.cell_width)
        total_height = self.header_height + (len(self.tasks) * self.row_height)
        self.configure(scrollregion=(0, 0, total_width, total_height))
        
        # 日付ヘッダーを描画
        current_date = start_date
        for i in range(days):
            x = self.task_width + (i * self.cell_width)
            # 日付
            self.create_text(x + self.cell_width/2, 15,
                           text=current_date.strftime('%d'),
                           anchor='center')
            # 月
            if i == 0 or current_date.day == 1:
                self.create_text(x + self.cell_width/2, 35,
                               text=current_date.strftime('%Y-%m'),
                               anchor='center')
            current_date += datetime.timedelta(days=1)
        
        # グリッドと各タスクを描画
        for i, task in enumerate(self.tasks):
            y = self.header_height + (i * self.row_height)
            
            # タスク名を描画
            self.create_text(5, y + self.row_height/2,
                           text=task['name'],
                           anchor='w')
            
            # タスクバーを描画
            task_start = datetime.datetime.strptime(task['start'], '%Y-%m-%d')
            task_end = datetime.datetime.strptime(task['end'], '%Y-%m-%d')
            start_x = self.task_width + ((task_start - start_date).days * self.cell_width)
            end_x = self.task_width + ((task_end - start_date).days * self.cell_width) + self.cell_width
            
            # 進捗バーの背景
            self.create_rectangle(start_x, y + 5,
                                end_x, y + self.row_height - 5,
                                fill='lightgray')
            
            # 進捗バー
            progress_width = (end_x - start_x) * (task['progress'] / 100)
            if progress_width > 0:
                self.create_rectangle(start_x, y + 5,
                                    start_x + progress_width, y + self.row_height - 5,
                                    fill='green')
            
            # 進捗率を表示
            self.create_text(start_x + (end_x - start_x)/2, y + self.row_height/2,
                           text=f"{task['progress']}%",
                           anchor='center')
        
        # グリッド線を描画
        self.create_line(self.task_width, 0, self.task_width, total_height, fill='gray')
        self.create_line(0, self.header_height, total_width, self.header_height, fill='gray')

class TaskEditor(tk.Toplevel):
    def __init__(self, parent, task=None):
        super().__init__(parent)
        self.title("タスク編集")
        self.task = task or {}
        self.result = None
        
        # ウィンドウを中央に配置
        window_width = 400
        window_height = 300
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        self.create_widgets()
    
    def create_widgets(self):
        # タスク名
        tk.Label(self, text="タスク名:").grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = tk.Entry(self, width=40)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)
        self.name_entry.insert(0, self.task.get('name', ''))
        
        # 開始日
        tk.Label(self, text="開始日:").grid(row=1, column=0, padx=5, pady=5)
        self.start_date = DateEntry(self, width=20, date_pattern='yyyy-mm-dd')
        self.start_date.grid(row=1, column=1, padx=5, pady=5)
        if 'start' in self.task:
            self.start_date.set_date(self.task['start'])
        
        # 終了日
        tk.Label(self, text="終了日:").grid(row=2, column=0, padx=5, pady=5)
        self.end_date = DateEntry(self, width=20, date_pattern='yyyy-mm-dd') # Changed to DateEntry
        self.end_date.grid(row=2, column=1, padx=5, pady=5)
        if 'end' in self.task:
            self.end_date.set_date(self.task['end'])
        
        # 進捗
        tk.Label(self, text="進捗 (%):").grid(row=3, column=0, padx=5, pady=5)
        self.progress_var = tk.StringVar(value=str(self.task.get('progress', 0)))
        self.progress_entry = tk.Entry(self, textvariable=self.progress_var, width=10)
        self.progress_entry.grid(row=3, column=1, sticky='w', padx=5, pady=5)
        
        # ボタン
        button_frame = tk.Frame(self)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        tk.Button(button_frame, text="保存", command=self.save).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT, padx=5)
    
    def save(self):
        try:
            progress = int(self.progress_var.get())
            if not (0 <= progress <= 100):
                raise ValueError("進捗は0から100の間で指定してください")
            
            self.result = {
                'name': self.name_entry.get(),
                'start': self.start_date.get_date().strftime('%Y-%m-%d'),
                'end': self.end_date.get_date().strftime('%Y-%m-%d'),
                'progress': progress
            }
            self.destroy()
        except ValueError as e:
            messagebox.showerror("エラー", str(e))
    
    def cancel(self):
        self.destroy()

class GanttChart(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.csv_analyzer = GeminiCSVAnalyzer()
        self.logger = logging.getLogger(__name__)
        self.tasks = []
        
        # エージェントの初期化
        self.task_agent = TaskAgent()
        self.chart_agent = ChartAgent()
        self.dialogue_agent = DialogueAgent()
        
        # UIの初期化
        self.setup_ui()
    
    def setup_ui(self):
        """UIコンポーネントの初期化と配置"""
        # ツールバーフレーム
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        # CSVインポートボタン
        import_btn = ttk.Button(toolbar, text="CSVインポート", command=self.import_csv)
        import_btn.pack(side=tk.LEFT, padx=5)

        # キャンバス（ガントチャート表示用）を GanttCanvas に変更
        self.canvas = GanttCanvas(self, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # テキスト入力エリア
        self.text_input = scrolledtext.ScrolledText(self, height=4)
        self.text_input.pack(fill=tk.X, padx=5, pady=5)

        # 自然言語コマンド実行ボタン
        command_btn = ttk.Button(self, text="コマンド実行", command=self.process_dialogue)
        command_btn.pack(pady=5)
    
    def convert_to_task_schema(self, raw_task):
        """CSVから読み込んだタスクデータをスキーマ形式に変換"""
        return {
            'id': str(uuid.uuid4()),
            'name': raw_task['name'],
            'start_date': raw_task['start_date'].isoformat(),
            'end_date': raw_task['end_date'].isoformat(),
            'progress': raw_task.get('progress', 0),
            'status': 'created',
            'dependencies': [],
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'duration': raw_task.get('duration', 0),
                'original_data': raw_task
            }
        }

    def update_gantt_chart(self):
        """ガントチャートを更新"""
        self.canvas.delete('all')
        
        if not self.tasks:
            return

        for i, task in enumerate(self.tasks):
            y = i * 30 + 10
            
            # タスク名と状態の表示
            status_colors = {
                'created': 'gray',
                'in_progress': 'blue',
                'completed': 'green'
            }
            
            # タスク名
            self.canvas.create_text(10, y, text=task['name'], anchor='w')
            
            # タスクバー
            start_date = pd.to_datetime(task['start_date'])
            end_date = pd.to_datetime(task['end_date'])
            
            x1 = self.date_to_x(start_date)
            x2 = self.date_to_x(end_date)
            
            # 進捗バーの描画
            bar_height = 20
            self.canvas.create_rectangle(x1, y - bar_height/2, x2, y + bar_height/2,
                                      fill=status_colors[task['status']],
                                      outline='darkgray')
            
            # 進捗率の表示
            if task['progress'] > 0:
                progress_x = x1 + (x2 - x1) * task['progress'] / 100
                self.canvas.create_rectangle(x1, y - bar_height/2, progress_x, y + bar_height/2,
                                          fill='lightgreen', outline='darkgreen')
            
            # 依存関係の矢印を描画
            for dep_id in task['dependencies']:
                dep_task = next((t for t in self.tasks if t['id'] == dep_id), None)
                if dep_task:
                    dep_index = self.tasks.index(dep_task)
                    dep_y = dep_index * 30 + 10
                    self.canvas.create_line(x1, y, x2, dep_y,
                                          arrow=tk.LAST, dash=(4, 2))
        
        self.draw_date_axis()

    def import_csv(self):
        """CSVファイルをインポート"""
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("CSVファイル", "*.csv")]
            )
            if file_path:
                mapping = self.csv_analyzer.analyze_csv_structure(file_path)
                if mapping:
                    df = pd.read_csv(file_path)
                    raw_tasks = self.csv_analyzer.validate_and_transform_data(df, mapping)
                    if raw_tasks:
                        # タスクデータをスキーマ形式に変換
                        tasks = [self.convert_to_task_schema(task) for task in raw_tasks]
                        # TaskAgentで処理
                        processed_tasks = self.task_agent.process_tasks(tasks)
                        self.set_tasks(processed_tasks)
                        messagebox.showinfo("成功", "CSVファイルを正常にインポートしました")
                    else:
                        raise ValueError("タスクデータの変換に失敗しました")
                else:
                    raise ValueError("CSVの構造解析に失敗しました")
        except Exception as e:
            self.logger.error(f"CSVインポート中にエラー: {str(e)}")
            messagebox.showerror("エラー", f"CSVのインポートに失敗しました: {str(e)}")

    def process_dialogue(self):
        """自然言語入力の処理"""
        try:
            user_input = self.text_input.get("1.0", tk.END).strip()
            if not user_input:
                return
                
            self.text_input.delete("1.0", tk.END)
            
            # DialogueAgentによる入力の解釈
            response = self.dialogue_agent.process_input(user_input, self.tasks)
            
            if response.get('action') == 'update_tasks':
                # TaskAgentによるタスクの更新
                updated_tasks = self.task_agent.process_tasks(response.get('tasks', []))
                self.set_tasks(updated_tasks)
            elif response.get('action') == 'update_chart':
                # ChartAgentによる表示設定の更新
                chart_settings = self.chart_agent.process_settings(response.get('settings', {}))
                self.update_chart_settings(chart_settings)
            
            messagebox.showinfo("処理結果", response.get('message', '処理が完了しました'))
            
        except Exception as e:
            self.logger.error(f"対話処理中にエラー: {str(e)}")
            messagebox.showerror("エラー", f"処理に失敗しました: {str(e)}")

    def update_chart_settings(self, settings):
        """チャート設定の更新"""
        try:
            if 'colors' in settings:
                # 色の設定を更新
                self.chart_colors = settings['colors']
            if 'display' in settings:
                # 表示設定を更新
                self.display_settings = settings['display']
            
            # チャートを再描画
            self.update_gantt_chart()
            
        except Exception as e:
            self.logger.error(f"チャート設定の更新中にエラー: {str(e)}")
            raise

    def set_tasks(self, tasks):
        """タスクリストを設定し、ガントチャートを更新"""
        try:
            # タスクの検証と前処理
            processed_tasks = self.task_agent.validate_tasks(tasks)
            self.tasks = processed_tasks
            self.update_gantt_chart()
            
        except Exception as e:
            self.logger.error(f"タスク設定中にエラー: {str(e)}")
            raise

    def draw_date_axis(self):
        """日付軸を描画"""
        if not self.tasks:
            return
        
        # プロジェクトの期間を取得
        all_dates = [pd.to_datetime(task['start_date']) for task in self.tasks] + \
                   [pd.to_datetime(task['end_date']) for task in self.tasks]
        project_start = min(all_dates)
        project_end = max(all_dates)
        
        # 日付軸の位置
        y = len(self.tasks) * self.canvas.row_height + self.canvas.header_height + 30
        
        # 軸の線を描画
        canvas_width = self.canvas.winfo_width() - 100
        self.canvas.create_line(100, y, 100 + canvas_width, y)
        
        # 日付ラベルを描画
        days = (project_end - project_start).days + 1
        for i in range(days):
            date = project_start + pd.Timedelta(days=i)
            x = self.canvas.task_width + ((date - pd.to_datetime(min(pd.to_datetime(task['start_date']) for task in self.tasks)))).days * self.canvas.cell_width
            self.canvas.create_line(x, y-5, x, y+5)  # 目盛り
            if i % 2 == 0:  # 2日おきに日付を表示
                self.canvas.create_text(x, y+20, text=date.strftime('%m/%d'),
                                              angle=45)

    def date_to_x(self, date):
        """日付をX座標に変換するメソッド"""
        if not self.tasks:
            return 0
        
        # プロジェクトの開始日を取得
        project_start = min(pd.to_datetime(task['start_date']) for task in self.tasks)
        
        # 日付の差分を計算してピクセル座標に変換
        days_diff = (date - project_start).days
        return self.canvas.task_width + (days_diff * self.canvas.cell_width)

def main():
    root = tk.Tk()
    root.title("ガントチャート")
    
    # ウィンドウサイズと位置を設定
    window_width = 1000
    window_height = 800
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    app = GanttChart(root)
    app.pack(fill=tk.BOTH, expand=True)
    
    root.mainloop()

if __name__ == '__main__':
    main()
