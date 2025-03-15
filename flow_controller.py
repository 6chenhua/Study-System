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
                q["id"] = f"{unit}_{content_type}_{subtype}_{i}"
            questions.extend(q_list)

        correct_count = 0
        wrong_questions = []
        for q in questions:
            q_id = q["id"]
            expected_answer = q["answer"]
            submitted_answer = answers.get(q_id)

            # 添加日志，区分 read_aloud 子类型
            if "read_aloud" in q_id:
                print(
                    f"Processing read_aloud question {q_id}: expected={expected_answer}, recognized={submitted_answer}")
            else:
                print(f"Processing question {q_id}: expected={expected_answer}, submitted={submitted_answer}")

            if submitted_answer == expected_answer:
                correct_count += 1
            else:
                q["user_answer"] = submitted_answer if submitted_answer is not None else None
                wrong_questions.append(q)

        question_count = len(questions)
        correct_rate = correct_count / question_count if question_count > 0 else 1.0
        print(
            f"Review {unit}_{content_type}: correct_count={correct_count}, question_count={question_count}, correct_rate={correct_rate}"
        )

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
        print(
            f"Practice {unit}_{content_type}: correct_count={correct_count}, question_count={question_count}, correct_rate={correct_rate}")

        # 更新 attempt 数据
        attempt["correct_rate"] = correct_rate
        attempt["wrong_questions"] = wrong_questions

        return {
            "correct_count": correct_count,
            "question_count": question_count,
            "correct_rate": correct_rate,
            "wrong_questions": wrong_questions
        }
