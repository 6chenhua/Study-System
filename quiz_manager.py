import json
from utils.llm import query_llm

# 调用deepseek模型判断读的是否正确
prompt = '''Scenario Description: 
A user reads an English text aloud and the system generates the corresponding audio. We use a speech-to-text tool to transcribe the audio into text to check the accuracy of the user's reading.
However, due to the possible error of the speech recognition tool, the transcription result may be slightly different from the actual content read by the user.

Task: 
Please determine whether the following two texts are basically the same, i.e. determine whether the transcription error comes from the speech recognition tool itself rather than the user reading aloud error. Note that you need to output in json format, the json output has two fields: one is_corrected, this field has only two values, they are true and false, true means that the user read aloud correctly, but the transcription tool recognition error; false: that the user read aloud incorrectly, the inaccuracy of the transcription result is the user's own problem. The other field is reason, which indicates the explanation of the judgment result.

The original text that the user should read aloud: {{text}} 
Speech recognition transcription result: {{transcribed_text}}
'''

class QuizManager:
    def __init__(self):
        self.prompt = prompt
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
            elif subtype == "read_aloud":
                prompt = self.prompt.replace("{{text}}", q["answer"]).replace("{{transcribed_text}}", user_answer)
                result = query_llm(prompt)
                print(result)
                res = json.loads(result)['is_corrected']
                if res.lower() == 'true':
                    correct_count += 1
            else:
                wrong_questions.append(q | {"user_answer": user_answer})
        total = len(questions)
        correct_rate = correct_count / total if total > 0 else 0
        return {"correct_rate": correct_rate, "wrong_questions": wrong_questions}
