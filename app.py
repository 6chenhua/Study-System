from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
from user_manager import UserManager
from schedule_manager import ScheduleManager
from quiz_manager import QuizManager
from flow_controller import FlowController
from utils.speech import recognize_speech  # 新增：导入语音识别模块

app = Flask(__name__)

user_manager = UserManager()
schedule_manager = ScheduleManager()
flow_controller = FlowController()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_id = request.form["user_id"]
        style = request.form["style"]
        user_state = user_manager.load_user(user_id)
        if not user_state:
            user_state = user_manager.init_user(user_id, style)

        day = user_state["current_day"]
        print(f"User {user_id} logged in, current_day: {day}")

        if user_state["progress"] == "completed":
            print("Course completed, redirecting to done")
            return redirect(url_for("done", user_id=user_id))

        tasks = schedule_manager.get_tasks(day)
        print(f"Tasks for day {day}: {tasks}")

        if not tasks:
            if day > schedule_manager.schedule["combined"]:
                user_state["progress"] = "completed"
                user_manager.save_user(user_state)
                print("Course completed, redirecting to done")
                return redirect(url_for("done", user_id=user_id))
            print(f"Day {day} is a rest day, redirecting to rest")
            return redirect(url_for("rest", user_id=user_id, day=day))
        else:
            video_watched = user_state.get("video_watched", {}).get(str(day), False)
            if any(task["attempt"] == 0 for task in tasks) and not video_watched:
                print(f"Day {day} has initial learning, redirecting to video")
                return redirect(url_for("video", user_id=user_id, day=day))
            print(f"Day {day} has review, redirecting to quiz")
            return redirect(url_for("quiz", user_id=user_id, day=day))

    return render_template("index.html")

@app.route("/video/<user_id>/<int:day>", methods=["GET", "POST"])
def video(user_id, day):
    user_state = user_manager.load_user(user_id)
    if not user_state:
        print(f"User {user_id} not found, redirecting to index")
        return redirect(url_for("index"))

    tasks = schedule_manager.get_tasks(day)
    if not tasks:
        print(f"No tasks for day {day}, redirecting to index")
        return redirect(url_for("index"))

    if request.method == "GET":
        # 生成视频路径（假设基于 unit 和 type）
        video_paths = []
        for task in tasks:
            if task["attempt"] == 0:  # 仅初学任务有视频
                # video_path = f"/static/videos/{user_state['style']}/{task['unit']}_{task['type']}_day{day}.mp4"
                video_path = f"/static/videos/{user_state['style']}/{task['unit']}_{task['type']}s_{user_state['style']}.mp4"
                video_paths.append(video_path)
        if not video_paths:
            print(f"No video available for day {day}, redirecting to quiz")
            return redirect(url_for("quiz", user_id=user_id, day=day))

        return render_template("video.html", user_id=user_id, day=day, video_paths=video_paths)

    elif request.method == "POST":
        # 更新 video_watched 状态
        if "video_watched" not in user_state:
            user_state["video_watched"] = {}
        user_state["video_watched"][str(day)] = True
        user_manager.save_user(user_state)

        # 从查询参数或 JSON 中获取 return_day（如果有）
        return_day = request.args.get("return_day", day, type=int)  # 默认返回当前 day
        print(f"Video watched for day {day}, redirecting to quiz for day {return_day}")
        return jsonify({"next": "quiz", "user_id": user_id, "day": return_day, "status": "success"})


@app.route("/update_video_watched/<user_id>/<int:day>", methods=["POST"])
def update_video_watched(user_id, day):
    user_state = user_manager.load_user(user_id)
    if not user_state:
        return jsonify({"status": "error", "message": "User not found"}), 404

    if "video_watched" not in user_state:
        user_state["video_watched"] = {}
    user_state["video_watched"][str(day)] = True
    user_manager.save_user(user_state)

    return_day = request.args.get("return_day", day, type=int)
    print(f"Updated video_watched for day {day}, redirecting to quiz for day {return_day}")
    return jsonify({"status": "success", "next": "quiz", "user_id": user_id, "day": return_day})

@app.route("/next_day/<user_id>/<int:day>")
def next_day(user_id, day):
    user_state = user_manager.load_user(user_id)
    if not user_state or user_state["progress"] == "completed":
        print(f"User {user_id} not found or course completed")
        return redirect(url_for("index"))

    next_day_num = day + 1
    next_tasks = schedule_manager.get_tasks(next_day_num)
    print(f"Next day: {next_day_num}, Tasks: {next_tasks}")

    if next_day_num > schedule_manager.schedule["combined"]:
        user_state["progress"] = "completed"
        user_manager.save_user(user_state)
        print("Course completed")
        return redirect(url_for("done", user_id=user_id))

    user_state["current_day"] = next_day_num
    user_manager.save_user(user_state)

    if not next_tasks:
        print(f"Day {next_day_num} is a rest day")
        return redirect(url_for("rest", user_id=user_id, day=next_day_num))
    else:
        if any(task["attempt"] == 0 for task in next_tasks):
            print(f"Next day {next_day_num} has initial learning, redirecting to video")
            return redirect(url_for("video", user_id=user_id, day=next_day_num))
        print(f"Next day {next_day_num} has review, redirecting to quiz")
        return redirect(url_for("quiz", user_id=user_id, day=next_day_num))

@app.route("/rest/<user_id>/<int:day>")
def rest(user_id, day):
    user_state = user_manager.load_user(user_id)
    if not user_state or user_state["progress"] == "completed":
        print(f"User {user_id} not found or course completed, redirecting to index")
        return redirect(url_for("index"))

    next_day = day + 1
    print(f"Showing rest page for user {user_id} on day {day}, next day {next_day}")
    return render_template("rest.html", user_id=user_id, day=day, next_day=next_day)


@app.route("/done/<user_id>")
def done(user_id):
    return render_template("done.html", user_id=user_id)


@app.route("/encourage/<user_id>/<int:day>", methods=["GET"])
def encourage(user_id, day):
    user_state = user_manager.load_user(user_id)
    if not user_state or user_state["progress"] == "completed":
        print(f"User {user_id} not found or course completed, redirecting to index")
        return redirect(url_for("index"))

    next_day = day + 1
    print(f"Showing encouragement page for user {user_id}, completed day {day}, next day {next_day}")
    return render_template("encourage.html", user_id=user_id, day=day, next_day=next_day)


@app.route("/quiz/<user_id>/<int:day>", methods=["GET", "POST"])
def quiz(user_id, day):
    user_state = user_manager.load_user(user_id)
    print(f"Loaded user_state in /quiz: {user_state}")
    if not user_state or user_state["progress"] == "completed":
        print(f"User {user_id} not found or course completed, redirecting to index")
        return redirect(url_for("index"))

    tasks = schedule_manager.get_tasks(day)
    print(f"Tasks for day {day}: {tasks}")
    if not tasks:
        next_day = day + 1
        user_state["current_day"] = next_day
        user_manager.save_user(user_state)
        print(f"No tasks for day {day}, moving to day {next_day}")
        if next_day > schedule_manager.schedule["combined"]:
            user_state["progress"] = "completed"
            user_manager.save_user(user_state)
            print("Course completed, redirecting to done")
            return redirect(url_for("done", user_id=user_id))
        print(f"Day {day} is a rest day, redirecting to rest")
        return redirect(url_for("rest", user_id=user_id, day=day))

    if "current_task_index" not in user_state or user_state["current_day"] != day:
        user_state["current_task_index"] = 0
        user_state["current_day"] = day
        user_manager.save_user(user_state)
        print(f"Reset current_task_index to 0 for day {day}")
    current_task_index = user_state["current_task_index"]
    print(f"Current task index: {current_task_index}, Total tasks: {len(tasks)}")

    if request.method == "GET":
        if current_task_index >= len(tasks):
            next_day = day + 1
            next_tasks = schedule_manager.get_tasks(next_day)
            print(f"All tasks for day {day} completed, next_day: {next_day}, next_tasks: {next_tasks}")
            user_state["current_task_index"] = 0
            user_state["current_day"] = next_day
            user_manager.save_user(user_state)

            if not next_tasks:
                if next_day > schedule_manager.schedule["combined"]:
                    user_state["progress"] = "completed"
                    user_manager.save_user(user_state)
                    print("Course completed, redirecting to done")
                    return redirect(url_for("done", user_id=user_id))
                print(f"Rest day for day {next_day}, redirecting to encourage")
                return redirect(url_for("encourage", user_id=user_id, day=day))
            else:
                print(f"Redirecting to encouragement page after completing day {day}")
                return redirect(url_for("encourage", user_id=user_id, day=day))

        current_task = tasks[current_task_index]
        print(f"Processing task {current_task_index + 1}/{len(tasks)}: {current_task}")

        video_watched = user_state.get("video_watched", {}).get(str(day), False)
        if current_task["attempt"] == 0 and not video_watched:
            print(f"Task {current_task_index + 1} requires video, redirecting to video")
            return redirect(url_for("video", user_id=user_id, day=day))

        questions = {}
        # 跟踪已添加的匹配题ID - 临时禁用过滤
        # added_matching_questions = set()
        
        for subtype in current_task["subtypes"]:
            key = f"{current_task['unit']}_{current_task['type']}_{subtype}"
            q_list = flow_controller.quiz_manager.get_questions(current_task["unit"], current_task["type"], subtype)
            print(f"获取到 {len(q_list)} 个 {key} 类型题目")
            
            # 对于匹配题，处理数据格式
            if subtype == "matching":
                # filtered_q_list = []
                
                for q in q_list:
                    # 记录原始数据格式，便于调试
                    print(f"原始匹配题数据: {q}")
                    
                    # 先处理新数据结构，添加兼容字段
                    if "left" in q and "right" in q:
                        # 添加兼容字段，确保代码其他部分可以正常工作
                        if "question" not in q:
                            q["question"] = f"Match: {q['left']}"
                        if "answer" not in q:
                            q["answer"] = q["right"]
                        if "options" not in q:
                            q["options"] = [q["right"]]  # 简单起见，只放入正确选项
                
                # 临时禁用匹配题过滤逻辑
                # q_list = filtered_q_list
                print(f"匹配题列表: {q_list}")
            
            for i, q in enumerate(q_list):
                q["id"] = f"{current_task['unit']}_{current_task['type']}_{subtype}_{i}"
                if subtype == "read_aloud": 
                    audio_filename = f"audio/{q['id']}.mp3"
                    if os.path.exists(os.path.join(app.static_folder, audio_filename)):
                        q["model_audio_url"] = url_for('static', filename=audio_filename)
                    else:
                        q["model_audio_url"] = None
                        app.logger.warning(f"Model audio file not found: static/{audio_filename} for question ID {q['id']}")
                elif subtype == "matching":
                    if ":" in q["question"]:
                        parts = q["question"].split(":", 1)
                        q["match_prompt"] = parts[0].strip()
                    else:
                        q["match_prompt"] = q["question"]
                elif subtype == "spelling":
                    if "answer" in q and isinstance(q["answer"], str):
                        import random
                        answer_letters = list(q["answer"])
                        random.shuffle(answer_letters)
                        q["shuffled_letters"] = answer_letters
                questions[key] = q_list
        task_info = [{"unit": current_task["unit"], "type": current_task["type"], "attempt": current_task["attempt"]}]
        print(f"Generated questions for task {current_task}: {questions}")
        return render_template("quiz.html", user_id=user_id, day=day, questions=questions, tasks=task_info)

    elif request.method == "POST":
        answers = {}
        for key_form in request.form:
            answers[key_form] = request.form[key_form]
            print(f"Received form answer for {key_form}: {answers[key_form]}")
            
            # 处理匹配题的JSON数据
            if "matching" in key_form and answers[key_form].startswith('[{'):
                try:
                    import json
                    # 解析JSON数据
                    match_data = json.loads(answers[key_form])
                    print(f"解析匹配题数据: {match_data}")
                    
                    # 对于匹配题，我们需要将所有连接都提交给后端
                    # 保持原始JSON格式，让流程控制器处理评分
                    # 不修改answers[key_form]的值
                except Exception as e:
                    print(f"解析匹配题JSON数据出错: {e}")
        
        for key_file in request.files:
            audio_file = request.files[key_file]
            print(f"Received audio file for {key_file}: {audio_file.filename}")
            recognized_text = recognize_speech(audio_file)
            answers[key_file] = recognized_text if recognized_text else ""
            print(f"Recognized text for {key_file}: {answers[key_file]}")

        current_task = tasks[current_task_index]
        task_answers = {k: v for k, v in answers.items() if
                        k.startswith(f"{current_task['unit']}_{current_task['type']}_")}
        print(f"Filtered task answers: {task_answers}")

        result = flow_controller.handle_review(user_state, current_task, task_answers)
        print(f"Task {current_task_index + 1}/{len(tasks)} result: {result}")

        correct_rate = result["correct_rate"]
        # threshold = 0.6 if current_task["attempt"] <= 1 else 0.7 if current_task["attempt"] == 2 else 0.8
        threshold = 0.6
        print(f"Correct rate: {correct_rate}, Threshold: {threshold}")

        video_day = day
        return_day = day
        if current_task["attempt"] > 0 and correct_rate < threshold:
            unit = current_task["unit"]
            content_type = current_task["type"]
            for past_day in range(1, day):
                past_tasks = schedule_manager.get_tasks(past_day)
                for task in past_tasks:
                    if task["unit"] == unit and task["type"] == content_type and task["attempt"] == 0:
                        video_day = past_day
                        return_day = day
                        print(f"Found initial learning day for {unit}_{content_type}: Day {video_day}")
                        break
                if video_day != day:
                    break

        if correct_rate < threshold:
            if "video_watched" in user_state and str(video_day) in user_state["video_watched"]:
                user_state["video_watched"][str(video_day)] = False
                print(f"Reset video_watched for day {video_day} due to task failure")

        user_manager.save_user(user_state)

        if correct_rate < threshold:
            print(f"Correct rate {correct_rate} < threshold {threshold}, redirecting to video for Day {video_day}")
            return jsonify({
                "next": "video",
                "user_id": user_id,
                "day": video_day,
                "return_day": return_day
            })
        elif correct_rate < 1.0:
            print(f"Correct rate {correct_rate} < 1.0, redirecting to practice")
            return jsonify({"next": "practice", "user_id": user_id, "day": day})
        else:
            user_state["current_task_index"] += 1
            print(f"Task {current_task_index + 1} completed, new index: {user_state['current_task_index']}")
            user_manager.save_user(user_state)

            if user_state["current_task_index"] < len(tasks):
                print(f"Moving to next task, redirecting to quiz")
                return jsonify({"next": "quiz", "user_id": user_id, "day": day})
            else:
                next_day = day + 1
                next_tasks = schedule_manager.get_tasks(next_day)
                print(f"All tasks completed, next_day: {next_day}, next_tasks: {next_tasks}")
                user_state["current_task_index"] = 0
                user_state["current_day"] = next_day
                user_manager.save_user(user_state)

                if not next_tasks:
                    if next_day > schedule_manager.schedule["combined"]:
                        user_state["progress"] = "completed"
                        user_manager.save_user(user_state)
                        print("Course completed, redirecting to done")
                        return jsonify({"next": "done", "user_id": user_id})
                    print(f"Rest day for day {next_day}, redirecting to encourage")
                    return jsonify({"next": "encourage", "user_id": user_id, "day": day})
                else:
                    print(f"Redirecting to encouragement page after completing day {day}")
                    return jsonify({"next": "encourage", "user_id": user_id, "day": day})


@app.route("/practice/<user_id>/<int:day>", methods=["GET", "POST"])
def practice(user_id, day):
    user_state = user_manager.load_user(user_id)
    print(f"Loaded user_state in /practice: {user_state}")
    if not user_state or user_state["progress"] == "completed":
        print(f"User {user_id} not found or course completed")
        return redirect(url_for("index"))

    tasks = schedule_manager.get_tasks(day)
    print(f"Tasks for day {day}: {tasks}")
    if not tasks:
        user_state["current_day"] += 1
        user_manager.save_user(user_state)
        print(f"No tasks for day {day}, moving to day {user_state['current_day']}")
        return redirect(url_for("index"))

    if "current_task_index" not in user_state or user_state["current_day"] != day:
        user_state["current_task_index"] = 0
        user_state["current_day"] = day
        user_manager.save_user(user_state)
        print(f"Reset current_task_index to 0 for day {day}")
    current_task_index = user_state["current_task_index"]
    print(f"Current task index: {current_task_index}, Total tasks: {len(tasks)}")

    if request.method == "GET":
        if current_task_index >= len(tasks):
            next_day = day + 1
            next_tasks = schedule_manager.get_tasks(next_day)
            print(f"All tasks completed for day {day}, next_day: {next_day}")
            user_state["current_task_index"] = 0
            user_state["current_day"] = next_day
            user_manager.save_user(user_state)
            if not next_tasks:
                if next_day > schedule_manager.schedule["combined"]:
                    user_state["progress"] = "completed"
                    user_manager.save_user(user_state)
                    return redirect(url_for("done", user_id=user_id))
                print(f"Rest day for day {next_day}, redirecting to encourage")
                return redirect(url_for("encourage", user_id=user_id, day=day))
            print(f"Redirecting to encouragement page after completing day {day}")
            return redirect(url_for("encourage", user_id=user_id, day=day))

        current_task = tasks[current_task_index]
        attempt = user_state["units"][current_task["unit"]][current_task["type"]]["attempts"][current_task["attempt"]]
        print(f"Attempt data for {current_task['unit']}_{current_task['type']}_attempt{current_task['attempt']}: {attempt}")

        # Prepare questions for the template, adding model_audio_url for read_aloud questions
        processed_questions_for_template = {}
        # wrong_questions is a list of question dicts according to user_state sample
        q_list_orig = attempt.get("wrong_questions", []) 
        q_type = current_task["type"] # Get the type from current_task

        # 跟踪已添加的匹配题ID
        added_matching_questions = set()
        
        q_list_processed = []
        for q_orig in q_list_orig:
            q_copy = q_orig.copy()
            if "read_aloud" in q_copy.get("id", "").lower():
                audio_filename = f"audio/{q_copy['id']}.mp3"
                if os.path.exists(os.path.join(app.static_folder, audio_filename)):
                    q_copy["model_audio_url"] = url_for('static', filename=audio_filename)
                else:
                    q_copy["model_audio_url"] = None
                    app.logger.warning(f"Model audio file not found for practice: static/{audio_filename} for question ID {q_copy['id']}")
            
            # 添加subtype字段
            if 'subtype' not in q_copy:
                if "choice" in q_copy.get("id", "").lower():
                    q_copy['subtype'] = 'choice'
                elif "matching" in q_copy.get("id", "").lower():
                    q_copy['subtype'] = 'matching'
                elif "read_aloud" in q_copy.get("id", "").lower():
                    q_copy['subtype'] = 'read_aloud'
            
            # 检查是否是匹配题，如果是则先处理兼容字段，再检查重复
            if "matching" in q_copy.get("id", "").lower() or q_type == "matching":
                # 先处理新数据结构，添加兼容字段
                if "left" in q_copy and "right" in q_copy:
                    # 添加兼容字段，确保代码其他部分可以正常工作
                    if "question" not in q_copy:
                        q_copy["question"] = f"Match: {q_copy['left']}"
                    if "answer" not in q_copy:
                        q_copy["answer"] = q_copy["right"]
                    if "options" not in q_copy:
                        q_copy["options"] = [q_copy["right"]]  # 简单起见，只放入正确选项
                    
                    # 使用新的数据格式时，创建唯一标识
                    content_key = f"{q_copy['left']}-{q_copy['right']}"
                else:
                    # 处理原始数据格式
                    content_key = f"{q_copy.get('question', '')}-{q_copy.get('answer', '')}"
                
                # 如果是重复的匹配题，跳过
                if content_key in added_matching_questions:
                    print(f"跳过重复的练习匹配题: {q_copy.get('id', content_key)}")
                    continue
                
                # 记录已添加的匹配题
                added_matching_questions.add(content_key)
                
            q_list_processed.append(q_copy)
            
        processed_questions_for_template[q_type] = q_list_processed
        
        active_question_list = processed_questions_for_template.get(q_type, [])
        if not active_question_list or attempt.get("correct_rate") == 1.0:
            print(f"No wrong questions to practice or all correct for task {current_task}, moving to next task in quiz")
            user_state["current_task_index"] += 1
            user_manager.save_user(user_state)
            return redirect(url_for("quiz", user_id=user_id, day=day))

        task_info = [{
            "unit": current_task["unit"],
            "type": current_task["type"],
            "attempt": current_task["attempt"],
            "subtypes": current_task.get("subtypes", [])
        }]
        print(f"Rendering practice with questions: {processed_questions_for_template}, task_info: {task_info}")
        return render_template("practice.html", user_id=user_id, day=day, questions=processed_questions_for_template, tasks=task_info)

    # POST 处理保持不变
    elif request.method == "POST":
        answers = {}
        for key_form in request.form:
            answers[key_form] = request.form[key_form]
            print(f"Received form answer for {key_form}: {answers[key_form]}")
        if "read_aloud" in tasks[current_task_index]["subtypes"]:
            for key_file in request.files:
                audio_file = request.files[key_file]
                print(f"Received audio file for {key_file}: {audio_file.filename}")
                recognized_text = recognize_speech(audio_file)
                answers[key_file] = recognized_text if recognized_text else ""
                print(f"Recognized text for {key_file}: {answers[key_file]}")

        current_task = tasks[current_task_index]
        task_answers = {k: v for k, v in answers.items() if k.startswith(f"{current_task['unit']}_{current_task['type']}_")}
        print(f"Filtered task answers: {task_answers}")

        result = flow_controller.handle_practice(user_state, current_task, task_answers)
        print(f"Practice result: {result}")

        user_manager.save_user(user_state)
        if result["correct_rate"] == 1.0:
            user_state["current_task_index"] += 1
            print(f"All correct, new index: {user_state['current_task_index']}")
            user_manager.save_user(user_state)
            if user_state["current_task_index"] >= len(tasks):
                next_day = day + 1
                next_tasks = schedule_manager.get_tasks(next_day)
                print(f"All tasks completed for day {day}, next_day: {next_day}")
                user_state["current_task_index"] = 0
                user_state["current_day"] = next_day
                user_manager.save_user(user_state)
                if not next_tasks:
                    if next_day > schedule_manager.schedule["combined"]:
                        user_state["progress"] = "completed"
                        user_manager.save_user(user_state)
                        return jsonify({"next": "done", "user_id": user_id})
                    print(f"Rest day for day {next_day}, redirecting to encourage")
                    return jsonify({"next": "encourage", "user_id": user_id, "day": day})
                else:
                    print(f"Redirecting to encouragement page after completing day {day}")
                    return jsonify({"next": "encourage", "user_id": user_id, "day": day})
            else:
                print(f"Moving to next task quiz")
                return jsonify({"next": "quiz", "user_id": user_id, "day": day})
        else:
            print(f"Not all correct, staying on practice")
            return jsonify({"next": "practice", "user_id": user_id, "day": day})



if __name__ == "__main__":
    os.makedirs("static/videos", exist_ok=True)
    app.run(debug=True)
