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
        correct_count = 0
        question_count = 0
        wrong_questions = {}

        for subtype in task["subtypes"]:
            questions = self.quiz_manager.get_questions(task["unit"], task["type"], subtype)
            print(f"Questions for {task['unit']}_{task['type']}_{subtype}: {questions}")
            for i, q in enumerate(questions):
                q_id = f"{task['unit']}_{task['type']}_{subtype}_{i}"
                print(f"Checking q_id: {q_id}, Expected answer: {q['answer']}")
                if q_id in answers:
                    question_count += 1
                    submitted_answer = answers[q_id]
                    expected_answer = q["answer"]
                    print(
                        f"Submitted: {submitted_answer}, Expected: {expected_answer}, Match: {submitted_answer == expected_answer}")
                    if submitted_answer == expected_answer:
                        correct_count += 1
                    else:
                        wrong_questions[q_id] = q
                else:
                    print(f"q_id {q_id} not found in answers")

        print(f"Result: correct_count={correct_count}, question_count={question_count}")
        return {
            "correct_count": correct_count,
            "question_count": question_count,
            "wrong_questions": wrong_questions
        }

    def handle_practice(self, user_state, task, answers):
        unit = task["unit"]
        content_type = task["type"]
        attempt_idx = task["attempt"]
        attempt = user_state["units"][unit][content_type]["attempts"][attempt_idx]
        subtypes = task["subtypes"]

        # 初始化统计变量
        total_correct = 0
        total_questions = 0
        wrong_questions = {}

        # 遍历所有子类型，处理仍需练习的错题
        for subtype in subtypes:
            if subtype in attempt["wrong_questions"] and attempt["wrong_questions"][subtype]:
                questions = attempt["wrong_questions"][subtype]  # 只检查当前错题
                subtype_result = self.quiz_manager.check_answers(answers, unit, content_type, subtype)
                total_questions += len(questions)

                # 检查每道题的正确性，更新错题列表
                current_wrong = []
                for q in questions:
                    q_id = q["id"]
                    correct_answer = q["answer"]
                    user_answer = answers.get(q_id, "")
                    if user_answer == correct_answer:
                        total_correct += 1
                    else:
                        current_wrong.append(q)
                wrong_questions[subtype] = current_wrong

        # 更新 attempt 数据
        correct_rate = total_correct / total_questions if total_questions > 0 else 1.0
        attempt["correct_rate"] = correct_rate
        attempt["wrong_questions"] = wrong_questions  # 覆盖旧数据，确保只保留当前错题

        # 返回统计结果
        return {
            "correct_count": total_correct,
            "question_count": total_questions,
            "wrong_questions": wrong_questions
        }

