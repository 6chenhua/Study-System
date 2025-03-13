import json

class QuizManager:
    def __init__(self):
        with open("data/quiz_data.json", "r", encoding="utf-8") as f:
            self.quiz_data = json.load(f)

    def get_questions(self, unit, content_type, subtype):
        if unit == "combined":
            unit = "unit1" if subtype in ["choice", "matching", "read_aloud", "spelling"] else "unit2"
            content_type = "word" if subtype in ["choice", "matching", "read_aloud", "spelling"] else "sentence"
        return self.quiz_data.get(unit, {}).get(content_type, {}).get(subtype, [])

    def check_answers(self, answers, unit, content_type, subtype):
        questions = self.get_questions(unit, content_type, subtype)
        correct_count = 0
        wrong_questions = []
        for q in questions:
            user_answer = answers.get(q["id"])
            if user_answer == q["answer"]:
                correct_count += 1
            else:
                wrong_questions.append(q | {"user_answer": user_answer})
        total = len(questions)
        correct_rate = correct_count / total if total > 0 else 0
        return {"correct_rate": correct_rate, "wrong_questions": wrong_questions}
