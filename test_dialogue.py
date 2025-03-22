import unittest
from agents import DialogueAgent
import logging

class TestDialogueAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # テスト全体の前処理
        logging.basicConfig(level=logging.ERROR)

    def setUp(self):
        self.agent = DialogueAgent()
        self.test_tasks = [
            {
                'id': '1',
                'name': 'タスクA',
                'start_date': '2024-03-01',
                'end_date': '2024-03-15',
                'progress': 0,
                'status': 'created',
                'dependencies': []
            },
            {
                'id': '2',
                'name': 'タスクB',
                'start_date': '2024-03-10',
                'end_date': '2024-03-25',
                'progress': 30,
                'status': 'in_progress',
                'dependencies': ['1']
            }
        ]

    def test_progress_update(self):
        """進捗更新のテスト"""
        # 基本的な進捗更新
        result = self.agent.process_input("タスクAの進捗を50%に更新", self.test_tasks)
        self.assertEqual(result['action'], 'update_tasks')
        self.assertEqual(result['tasks'][0]['progress'], 50)
        
        # パーセント記号なしの更新
        result = self.agent.process_input("タスクBを80に更新", self.test_tasks)
        self.assertEqual(result['tasks'][1]['progress'], 80)
        
        # 完了状態への更新
        result = self.agent.process_input("タスクAを100%完了", self.test_tasks)
        self.assertEqual(result['tasks'][0]['status'], 'completed')

    def test_invalid_inputs(self):
        """無効な入力のテスト"""
        # タスク名なし
        result = self.agent.process_input("進捗を50%に更新", self.test_tasks)
        self.assertEqual(result['action'], 'none')
        
        # 進捗率なし
        result = self.agent.process_input("タスクAの進捗を更新", self.test_tasks)
        self.assertEqual(result['action'], 'none')
        
        # 存在しないタスク
        result = self.agent.process_input("タスクCの進捗を50%に更新", self.test_tasks)
        self.assertEqual(result['action'], 'none')
        
        # 無効な進捗率
        result = self.agent.process_input("タスクAの進捗を120%に更新", self.test_tasks)
        self.assertEqual(result['action'], 'none')

    def test_status_commands(self):
        """ステータス変更のテスト"""
        # 開始コマンド
        result = self.agent.process_input("タスクAを開始", self.test_tasks)
        self.assertEqual(result['tasks'][0]['status'], 'in_progress')
        
        # 完了コマンド
        result = self.agent.process_input("タスクAを完了", self.test_tasks)
        self.assertEqual(result['tasks'][0]['status'], 'completed')
        self.assertEqual(result['tasks'][0]['progress'], 100)

    def test_natural_language_variations(self):
        """自然言語バリエーションのテスト"""
        variations = [
            "タスクAの進捗率を50パーセントに設定",
            "タスクAを50%まで進める",
            "タスクAの進捗状況を50%にする",
            "タスクAの完了率を50%に変更"
        ]
        
        for command in variations:
            result = self.agent.process_input(command, self.test_tasks)
            self.assertEqual(result['action'], 'update_tasks')
            self.assertEqual(result['tasks'][0]['progress'], 50)

    def test_multiple_commands(self):
        """複数コマンドのテスト"""
        result = self.agent.process_input("""
            タスクAを開始
            タスクAの進捗を30%に更新
            タスクBを完了
        """, self.test_tasks)
        
        self.assertEqual(result['tasks'][0]['status'], 'in_progress')
        self.assertEqual(result['tasks'][0]['progress'], 30)
        self.assertEqual(result['tasks'][1]['status'], 'completed')

if __name__ == '__main__':
    unittest.main() 