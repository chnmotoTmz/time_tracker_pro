from agents import DialogueAgent

def test_dialogue_sequence():
    """対話テストシーケンス"""
    test_commands = [
        # 基本的な進捗更新
        "タスクAの進捗を50%に更新",
        
        # 様々な進捗更新の表現
        "タスクBを80%まで進める",
        "タスクAの完了率を60%にする",
        "タスクBの進捗状況を90%に設定",
        
        # ステータス変更
        "タスクAを開始",
        "タスクBを完了",
        
        # エラーケース
        "存在しないタスクの進捗を50%に更新",
        "タスクAの進捗を120%に更新",
        "進捗を50%に更新",
        
        # 複数行コマンド
        """
        タスクAを開始
        タスクAの進捗を30%に更新
        タスクBを完了
        """
    ]
    
    agent = DialogueAgent()
    tasks = [
        {
            'id': '1',
            'name': 'タスクA',
            'start_date': '2024-03-01',
            'end_date': '2024-03-15',
            'progress': 0,
            'status': 'created'
        },
        {
            'id': '2',
            'name': 'タスクB',
            'start_date': '2024-03-10',
            'end_date': '2024-03-25',
            'progress': 30,
            'status': 'in_progress'
        }
    ]
    
    for command in test_commands:
        print(f"\n実行コマンド: {command}")
        result = agent.process_input(command, tasks)
        print(f"結果: {result['message']}")
        if result['action'] == 'update_tasks':
            tasks = result['tasks']
            print("更新後のタスク状態:")
            for task in tasks:
                print(f"- {task['name']}: 進捗{task['progress']}%, 状態{task['status']}")

if __name__ == '__main__':
    test_dialogue_sequence() 