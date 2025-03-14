# from quiz_manager import QuizManager
#
# class FlowController:
#     def __init__(self):
#         self.quiz_manager = QuizManager()
#
#     def process_task(self, user_state, day, task):
#         attempt_idx = task["attempt"]
#         unit = task["unit"]
#         content_type = task["type"]
#         attempts = user_state["units"][unit][content_type]["attempts"]
#
#         if attempt_idx == 0:  # 初学
#             return {"next": "video", "data": {}}
#         else:  # 复习
#             questions = {}
#             for subtype in task["subtypes"]:
#                 questions[subtype] = self.quiz_manager.get_questions(unit, content_type, subtype)
#             return {"next": "quiz", "data": {"questions": questions}}
#
#     def handle_review(self, user_state, task, answers):
#         """
#         处理用户的quiz答案，计算正确率并记录错题。
#
#         参数:
#             user_state: 用户状态字典，包含学习进度和历史数据
#             task: 当前任务字典，包含unit、type、subtypes和attempt等信息
#             answers: 用户提交的答案字典，键为question_id，值为用户答案
#
#         返回:
#             dict: 包含correct_count、question_count和wrong_questions的结果
#         """
#         unit = task["unit"]  # e.g., "unit1"
#         content_type = task["type"]  # e.g., "word" 或 "sentence"
#         subtypes = task["subtypes"]  # e.g., ["choice", "matching"]
#
#         # 获取当前任务的所有问题
#         questions = []
#         for subtype in subtypes:
#             subtype_questions = self.quiz_manager.get_questions(unit, content_type, subtype)
#             questions.extend(subtype_questions)
#
#         # 计算正确答案数量和错题
#         correct_count = 0
#         wrong_questions = {}  # 按题型分组的错题字典
#
#         for q in questions:
#             q_id = q["id"]  # e.g., "unit1_word_choice_0"
#             correct_answer = q["answer"]
#             user_answer = answers.get(q_id)  # 用户提交的答案，可能为None
#
#             # 提取题型（从q_id中解析）
#             subtype = q_id.split("_")[2]  # 假设格式为"unit1_word_choice_0"，取"choice"
#
#             # 初始化题型对应的错题数组
#             if subtype not in wrong_questions:
#                 wrong_questions[subtype] = []
#
#             # 检查答案是否正确
#             if user_answer == correct_answer:
#                 correct_count += 1
#             else:
#                 # 记录错题信息
#                 wrong_info = {
#                     "id": q_id,
#                     "answer": correct_answer,
#                     "user_answer": user_answer if user_answer is not None else "未回答"
#                 }
#                 wrong_questions[subtype].append(wrong_info)
#
#         # 计算总数
#         question_count = len(questions)
#
#         # 返回结果
#         result = {
#             "correct_count": correct_count,
#             "question_count": question_count,
#             "wrong_questions": wrong_questions
#         }
#         print(f"handle_review result: {result}")
#         return result
#
#     def handle_practice(self, user_state, task, answers):
#         unit = task["unit"]
#         content_type = task["type"]
#         attempt_idx = task["attempt"]
#         attempt = user_state["units"][unit][content_type]["attempts"][attempt_idx]
#         subtypes = task["subtypes"]
#
#         # 初始化统计变量
#         total_correct = 0
#         total_questions = 0
#         wrong_questions = {}
#
#         # 遍历所有子类型，处理仍需练习的错题
#         for subtype in subtypes:
#             if subtype in attempt["wrong_questions"] and attempt["wrong_questions"][subtype]:
#                 questions = attempt["wrong_questions"][subtype]  # 只检查当前错题
#                 subtype_result = self.quiz_manager.check_answers(answers, unit, content_type, subtype)
#                 total_questions += len(questions)
#
#                 # 检查每道题的正确性，更新错题列表
#                 current_wrong = []
#                 for q in questions:
#                     q_id = q["id"]
#                     correct_answer = q["answer"]
#                     user_answer = answers.get(q_id, "")
#                     if user_answer == correct_answer:
#                         total_correct += 1
#                     else:
#                         current_wrong.append(q)
#                 wrong_questions[subtype] = current_wrong
#
#         # 更新 attempt 数据
#         correct_rate = total_correct / total_questions if total_questions > 0 else 1.0
#         attempt["correct_rate"] = correct_rate
#         attempt["wrong_questions"] = wrong_questions  # 覆盖旧数据，确保只保留当前错题
#
#         # 返回统计结果
#         return {
#             "correct_count": total_correct,
#             "question_count": total_questions,
#             "wrong_questions": wrong_questions
#         }

from quiz_manager import QuizManager

class FlowController:
    def __init__(self):
        self.quiz_manager = QuizManager()

    def process_task(self, user_state, day, task):
        attempt_idx = task["attempt"]
        unit = task["unit"]
        content_type = task["type"]
        attempts = user_state["units"][unit][content_type]["attempts"]

        if attempt_idx == 0:  # 初学
            return {"next": "video", "data": {}}
        else:  # 复习
            questions = {}
            for subtype in task["subtypes"]:
                questions[subtype] = self.quiz_manager.get_questions(unit, content_type, subtype)
            return {"next": "quiz", "data": {"questions": questions}}

    def handle_review(self, user_state, task, answers):
        unit = task["unit"]
        content_type = task["type"]
        attempt_idx = task["attempt"]

        # 初始化 units 结构
        if "units" not in user_state:
            user_state["units"] = {}
        if unit not in user_state["units"]:
            user_state["units"][unit] = {}
        if content_type not in user_state["units"][unit]:
            user_state["units"][unit][content_type] = {"attempts": []}

        attempts = user_state["units"][unit][content_type]["attempts"]
        while len(attempts) <= attempt_idx:
            attempts.append({"day": user_state["current_day"], "correct_rate": 0.0, "wrong_questions": []})

        # 计算所有题目的正确率（按 subtype 分组生成一致的 ID）
        questions = []
        for subtype in task["subtypes"]:
            q_list = self.quiz_manager.get_questions(unit, content_type, subtype)
            for i, q in enumerate(q_list):
                # 与 /quiz 中的 ID 生成保持一致
                q["id"] = f"{unit}_{content_type}_{subtype}_{i}"
            questions.extend(q_list)

        correct_count = 0
        wrong_questions = []
        for q in questions:
            q_id = q["id"]  # 使用预生成的 ID
            expected_answer = q["answer"]
            submitted_answer = answers.get(q_id)
            if submitted_answer == expected_answer:
                correct_count += 1
            else:
                q["user_answer"] = submitted_answer if submitted_answer is not None else None
                wrong_questions.append(q)

        question_count = len(questions)
        correct_rate = correct_count / question_count if question_count > 0 else 1.0
        print(
            f"Review {unit}_{content_type}: correct_count={correct_count}, question_count={question_count}, correct_rate={correct_rate}")

        # 更新 attempt 数据
        attempts[attempt_idx] = {
            "day": user_state["current_day"],
            "correct_rate": correct_rate,
            "wrong_questions": wrong_questions
        }

        return {
            "correct_count": correct_count,
            "question_count": question_count,
            "correct_rate": correct_rate,
            "wrong_questions": wrong_questions
        }

    def handle_practice(self, user_state, task, answers):
        unit = task["unit"]
        content_type = task["type"]
        attempt_idx = task["attempt"]
        attempt = user_state["units"][unit][content_type]["attempts"][attempt_idx]

        questions = attempt["wrong_questions"]
        correct_count = 0
        wrong_questions = []

        for q in questions:
            q_id = q["id"]
            correct_answer = q["answer"]
            user_answer = answers.get(q_id, "")
            if user_answer == correct_answer:
                correct_count += 1
            else:
                q["user_answer"] = user_answer
                wrong_questions.append(q)

        question_count = len(questions)
        correct_rate = correct_count / question_count if question_count > 0 else 1.0
        print(f"Practice {unit}_{content_type}: correct_count={correct_count}, question_count={question_count}, correct_rate={correct_rate}")

        # 更新 attempt 数据
        attempt["correct_rate"] = correct_rate
        attempt["wrong_questions"] = wrong_questions

        return {
            "correct_count": correct_count,
            "question_count": question_count,
            "correct_rate": correct_rate,
            "wrong_questions": wrong_questions
        }
