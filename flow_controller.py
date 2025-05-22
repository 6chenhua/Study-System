import json

from quiz_manager import QuizManager
from utils.llm import query_llm

LLM_PROMPT_TEMPLATE = '''Scenario Description: 
A user reads an English text aloud and the system generates the corresponding audio. We use a speech-to-text tool to transcribe the audio into text to check the accuracy of the user's reading.
However, due to the possible error of the speech recognition tool, the transcription result may be slightly different from the actual content read by the user.

Task: 
Please determine whether the following two texts are basically the same, i.e. determine whether the transcription error comes from the speech recognition tool itself rather than the user reading aloud error. Note that you need to output in json format, the json output has two fields: one is_corrected, this field has only two values, they are "true" and "false" (STRING FORMAT), true means that the user read aloud correctly, but the transcription tool recognition error; false: that the user read aloud incorrectly, the inaccuracy of the transcription result is the user's own problem. The other field is reason, which indicates the explanation of the judgment result.

The original text that the user should read aloud: {{text}} 
Speech recognition transcription result: {{transcribed_text}}

Please try to check as loosely as possible, because the model used for transcription doesn't perform very well.
'''

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
        
        # 查找匹配题的JSON数据 - 现在可能只有第一个匹配题提交了包含所有匹配对的JSON
        first_matching_json = None
        for key, value in answers.items():
            if "matching" in key and value and value.startswith('[{'):
                try:
                    first_matching_json = json.loads(value)
                    print(f"找到匹配题JSON数据: {first_matching_json}")
                    break
                except Exception as e:
                    print(f"解析匹配题JSON数据出错: {e}")
        
        # 提取所有匹配题
        matching_questions = [q for q in questions if "matching" in q["id"]]
        # 标记已处理的匹配题
        processed_matching_ids = []
        
        for q in questions:
            q_id = q["id"]
            # 安全获取答案字段 - 添加默认值以避免KeyError
            expected_answer = q.get("answer", "")
            
            # 如果没有answer字段但有right字段，将right字段作为答案
            if not expected_answer and "right" in q:
                expected_answer = q["right"]
            
            submitted_answer = answers.get(q_id)
            
            # 处理read_aloud子类型
            if "read_aloud" in q_id:
                print(f"Processing read_aloud question {q_id}: expected={expected_answer}, recognized={submitted_answer}")
                if submitted_answer:
                    try:
                        # 为每次调用创建一个新的prompt字符串
                        current_prompt = LLM_PROMPT_TEMPLATE.replace("{{text}}", expected_answer).replace("{{transcribed_text}}", submitted_answer)
                        result = query_llm(current_prompt)
                        print(f"LLM response for {q_id}: {result}")
                        
                        if result and result.strip():
                            # 解析JSON结果
                            result_json = json.loads(result)
                            is_correct = result_json.get('is_corrected', '').lower() == 'true'
                            
                            if is_correct:
                                correct_count += 1
                                # 朗读题已处理完毕，跳过下面的通用评分逻辑
                                continue
                            # 不正确的情况会进入下面的else分支
                    except Exception as e:
                        print(f"Error processing LLM for {q_id}: {e}")
                        # 发生错误时，回退到精确匹配
            # 处理图片选择题 - 和普通选择题相同的评分逻辑
            elif "image_choice" in q_id or q.get("subtype") == "image_choice":
                print(f"处理图片选择题 {q_id}: 预期答案={expected_answer}, 提交答案={submitted_answer}")
                if submitted_answer == expected_answer:
                    correct_count += 1
                    continue
                else:
                    q["user_answer"] = submitted_answer if submitted_answer is not None else None
                    wrong_questions.append(q)
                    continue
            # 处理匹配题 - 新的集中处理逻辑
            elif "matching" in q_id and q_id not in processed_matching_ids:
                # 收集匹配题数据
                match_data = None
                
                # 尝试使用此题目提交的答案
                if submitted_answer and submitted_answer.startswith('[{'):
                    try:
                        match_data = json.loads(submitted_answer)
                    except Exception as e:
                        print(f"解析当前匹配题数据出错: {e}")
                        match_data = None
                
                # 如果没有当前题目的提交答案，但有第一个匹配题的JSON数据
                if not match_data and first_matching_json:
                    match_data = first_matching_json
                    print(f"使用第一个匹配题的JSON数据评分 {q_id}")
                
                if match_data:
                    # 处理所有匹配题
                    correct_matches = 0  # 计算正确的匹配数量
                    total_matches = len(matching_questions)  # 总匹配题数量
                    
                    for match_q in matching_questions:
                        match_id = match_q["id"]
                        processed_matching_ids.append(match_id)  # 标记为已处理
                        
                        # 提取预期答案
                        expected_left_text = ""
                        expected_right_text = ""
                        
                        if "left" in match_q and "right" in match_q:
                            expected_left_text = match_q["left"]
                            expected_right_text = match_q["right"]
                        elif isinstance(match_q.get("answer", ""), str):
                            expected_right_text = match_q.get("answer", "")
                            
                            # 从question中提取左侧文本
                            question_text = match_q.get("question", "")
                            if ":" in question_text:
                                expected_left_text = question_text.split(":", 1)[1].strip()
                            else:
                                expected_left_text = question_text
                        elif isinstance(match_q.get("answer", ""), dict) and "right" in match_q.get("answer", ""):
                            expected_right_text = match_q["answer"]["right"]
                            expected_left_text = match_q["answer"].get("left", "")
                        else:
                            expected_right_text = match_q.get("options", [""])[0]  # 默认取第一个选项
                            
                            # 从question中提取左侧文本
                            question_text = match_q.get("question", "")
                            if ":" in question_text:
                                expected_left_text = question_text.split(":", 1)[1].strip()
                            else:
                                expected_left_text = question_text
                        
                        print(f"匹配题预期答案: 左侧='{expected_left_text}', 右侧='{expected_right_text}'")
                        
                        # 检查是否找到正确匹配
                        is_correct = False
                        for conn in match_data:
                            left_text = conn.get("left", "")
                            right_text = conn.get("right", "")
                            
                            if left_text == expected_left_text and right_text == expected_right_text:
                                is_correct = True
                                print(f"找到正确匹配: '{left_text}' - '{right_text}'")
                                break
                        
                        if is_correct:
                            correct_matches += 1  # 增加正确匹配计数
                            print(f"匹配题 {match_id} 回答正确")
                        else:
                            match_q["user_answer"] = json.dumps(match_data)
                            wrong_questions.append(match_q)
                            print(f"匹配题 {match_id} 回答错误")
                    
                    # 将正确匹配的数量加到总正确数上
                    correct_count += correct_matches
                    print(f"匹配题总数: {total_matches}, 正确匹配数: {correct_matches}")
                    
                    # 已处理所有匹配题，跳过当前题目
                    continue
                else:
                    # 如果没有匹配数据，标记所有匹配题为错误
                    for match_q in matching_questions:
                        match_id = match_q["id"]
                        processed_matching_ids.append(match_id)  # 标记为已处理
                        match_q["user_answer"] = None
                        wrong_questions.append(match_q)
                        print(f"没有找到匹配题 {match_id} 的提交数据")
                    
                    # 已处理所有匹配题，跳过当前题目
                    continue
            
            # 跳过已处理的匹配题
            if "matching" in q_id and q_id in processed_matching_ids:
                continue
                
            else:
                print(f"Processing question {q_id}: expected={expected_answer}, submitted={submitted_answer}")

            # 只处理未被添加到wrong_questions的题目
            if q_id not in [wq["id"] for wq in wrong_questions]:
                # 对于一般题型，使用精确匹配
                if submitted_answer == expected_answer:
                    correct_count += 1
                else:
                    q["user_answer"] = submitted_answer if submitted_answer is not None else None
                    wrong_questions.append(q)

        # 清理所有问题中的临时标记
        for q in questions:
            if "already_processed" in q:
                del q["already_processed"]

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
        
        # 查找匹配题的JSON数据
        first_matching_json = None
        for key, value in answers.items():
            if "matching" in key and value and value.startswith('[{'):
                try:
                    first_matching_json = json.loads(value)
                    print(f"找到练习匹配题JSON数据: {first_matching_json}")
                    break
                except Exception as e:
                    print(f"解析练习匹配题JSON数据出错: {e}")
        
        # 提取所有匹配题
        matching_questions = [q for q in questions if "matching" in q["id"]]
        # 标记已处理的匹配题
        processed_matching_ids = []

        for q in questions:
            q_id = q["id"]
            # 安全获取答案字段 - 添加默认值以避免KeyError
            expected_answer = q.get("answer", "")
            
            # 如果没有answer字段但有right字段，将right字段作为答案
            if not expected_answer and "right" in q:
                expected_answer = q["right"]
            
            submitted_answer = answers.get(q_id)
            
            # 区分处理read_aloud题型
            if "read_aloud" in q_id and submitted_answer:
                try:
                    # 为每次调用创建一个新的prompt字符串
                    current_prompt = LLM_PROMPT_TEMPLATE.replace("{{text}}", expected_answer).replace("{{transcribed_text}}", submitted_answer)
                    result = query_llm(current_prompt)
                    print(f"LLM response for {q_id}: {result}")
                    
                    if result and result.strip():
                        # 解析JSON结果
                        result_json = json.loads(result)
                        is_correct = result_json.get('is_corrected', '').lower() == 'true'
                        
                        if is_correct:
                            correct_count += 1
                            # 标记为已处理
                            q["already_processed"] = True
                            continue
                except Exception as e:
                    print(f"Error processing LLM for practice {q_id}: {e}")
                # 标记已处理，无论成功与否
                q["already_processed"] = True
            
            # 处理图片选择题 - 和普通选择题相同的评分逻辑
            elif "image_choice" in q_id or q.get("subtype") == "image_choice":
                print(f"处理图片选择题 {q_id}: 预期答案={expected_answer}, 提交答案={submitted_answer}")
                if submitted_answer == expected_answer:
                    correct_count += 1
                    continue
                else:
                    q["user_answer"] = submitted_answer if submitted_answer is not None else None
                    wrong_questions.append(q)
                    continue
            
            # 处理匹配题 - 集中处理所有匹配题
            elif "matching" in q_id and q_id not in processed_matching_ids and len(matching_questions) > 0:
                # 收集匹配题数据
                match_data = None
                
                # 尝试使用此题目提交的答案
                if submitted_answer and submitted_answer.startswith('[{'):
                    try:
                        match_data = json.loads(submitted_answer)
                    except Exception as e:
                        print(f"解析当前练习匹配题数据出错: {e}")
                        match_data = None
                
                # 如果没有当前题目的提交答案，但有第一个匹配题的JSON数据
                if not match_data and first_matching_json:
                    match_data = first_matching_json
                    print(f"使用第一个匹配题的JSON数据评分练习 {q_id}")
                
                if match_data:
                    # 处理所有匹配题
                    correct_matches = 0  # 计算正确的匹配数量
                    total_matches = len(matching_questions)  # 总匹配题数量
                    
                    for match_q in matching_questions:
                        match_id = match_q["id"]
                        processed_matching_ids.append(match_id)  # 标记为已处理
                        
                        # 提取预期答案
                        expected_left_text = ""
                        expected_right_text = ""
                        
                        if "left" in match_q and "right" in match_q:
                            expected_left_text = match_q["left"]
                            expected_right_text = match_q["right"]
                        elif isinstance(match_q.get("answer", ""), str):
                            expected_right_text = match_q.get("answer", "")
                            
                            # 从question中提取左侧文本
                            question_text = match_q.get("question", "")
                            if ":" in question_text:
                                expected_left_text = question_text.split(":", 1)[1].strip()
                            else:
                                expected_left_text = question_text
                        elif isinstance(match_q.get("answer", ""), dict) and "right" in match_q.get("answer", ""):
                            expected_right_text = match_q["answer"]["right"]
                            expected_left_text = match_q["answer"].get("left", "")
                        else:
                            expected_right_text = match_q.get("options", [""])[0]  # 默认取第一个选项
                            
                            # 从question中提取左侧文本
                            question_text = match_q.get("question", "")
                            if ":" in question_text:
                                expected_left_text = question_text.split(":", 1)[1].strip()
                            else:
                                expected_left_text = question_text
                        
                        print(f"练习匹配题预期答案: 左侧='{expected_left_text}', 右侧='{expected_right_text}'")
                        
                        # 检查是否找到正确匹配
                        is_correct = False
                        for conn in match_data:
                            left_text = conn.get("left", "")
                            right_text = conn.get("right", "")
                            
                            if left_text == expected_left_text and right_text == expected_right_text:
                                is_correct = True
                                print(f"找到正确练习匹配: '{left_text}' - '{right_text}'")
                                break
                        
                        if is_correct:
                            correct_matches += 1  # 增加正确匹配计数
                            print(f"练习匹配题 {match_id} 回答正确")
                        else:
                            match_q["user_answer"] = json.dumps(match_data)
                            wrong_questions.append(match_q)
                            print(f"练习匹配题 {match_id} 回答错误")
                    
                    # 将正确匹配的数量加到总正确数上
                    correct_count += correct_matches
                    print(f"练习匹配题总数: {total_matches}, 正确匹配数: {correct_matches}")
                    
                    # 已处理所有匹配题，跳过当前题目
                    continue
                else:
                    # 如果没有匹配数据，标记所有匹配题为错误
                    for match_q in matching_questions:
                        match_id = match_q["id"]
                        processed_matching_ids.append(match_id)  # 标记为已处理
                        match_q["user_answer"] = None
                        wrong_questions.append(match_q)
                        print(f"没有找到练习匹配题 {match_id} 的提交数据")
                    
                    # 已处理所有匹配题，跳过当前题目
                    continue
            
            # 跳过已处理的匹配题
            if "matching" in q_id and q_id in processed_matching_ids:
                continue
                
            else:
                # 对于一般题型和未识别的题型，只处理未被添加到wrong_questions的题目
                if q_id not in [wq["id"] for wq in wrong_questions]:
                    if submitted_answer == expected_answer:
                        correct_count += 1
                    else:
                        q["user_answer"] = submitted_answer
                        wrong_questions.append(q)

        # 清理所有问题中的临时标记
        for q in questions:
            if "already_processed" in q:
                del q["already_processed"]

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
