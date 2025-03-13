from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
from user_manager import UserManager
from schedule_manager import ScheduleManager
from quiz_manager import QuizManager
from flow_controller import FlowController

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

@app.route("/video/<user_id>/<int:day>")
def video(user_id, day):
    user_state = user_manager.load_user(user_id)
    if not user_state or user_state["progress"] == "completed":
        return redirect(url_for("index"))

    tasks = schedule_manager.get_tasks(day)
    if not tasks:
        user_state["current_day"] += 1
        user_manager.save_user(user_state)
        return redirect(url_for("video", user_id=user_id, day=user_state["current_day"]))

    video_paths = [f"/static/videos/{user_state['style']}_{task['unit']}_{task['type']}_day{day}.mp4" for task in tasks]
    return render_template("video.html", video_paths=video_paths, user_id=user_id, day=day)

@app.route("/update_video_watched/<user_id>/<int:day>", methods=["POST"])
def update_video_watched(user_id, day):
    user_state = user_manager.load_user(user_id)
    if not user_state:
        return jsonify({"error": "User not found"}), 404

    if "video_watched" not in user_state:
        user_state["video_watched"] = {}
    user_state["video_watched"][str(day)] = True
    user_manager.save_user(user_state)
    return jsonify({"status": "success"})

@app.route("/quiz/<user_id>/<int:day>", methods=["GET", "POST"])
def quiz(user_id, day):
    user_state = user_manager.load_user(user_id)
    if not user_state or user_state["progress"] == "completed":
        print(f"User {user_id} not found or course completed")
        return redirect(url_for("index"))

    tasks = schedule_manager.get_tasks(day)
    print(f"Tasks for day {day}: {tasks}")
    if not tasks:
        user_state["current_day"] += 1
        user_manager.save_user(user_state)
        print(f"No tasks for day {day}, moving to day {user_state['current_day']}")
        return redirect(url_for("video", user_id=user_id, day=user_state["current_day"]))

    if request.method == "GET":
        questions = {}
        task_info = []
        video_watched = user_state.get("video_watched", {}).get(str(day), False)

        for task in tasks:
            if task["attempt"] == 0 and not video_watched:
                return redirect(url_for("video", user_id=user_id, day=day))
            for subtype in task["subtypes"]:
                key = f"{task['unit']}_{task['type']}_{subtype}"
                q_list = flow_controller.quiz_manager.get_questions(task["unit"], task["type"], subtype)
                # 为每道题设置唯一的 id
                for i, q in enumerate(q_list):
                    q["id"] = f"{task['unit']}_{task['type']}_{subtype}_{i}"
                questions[key] = q_list
            task_info.append({"unit": task["unit"], "type": task["type"], "attempt": task["attempt"]})
        print(f"Generated questions: {questions}")
        return render_template("quiz.html", user_id=user_id, day=day, questions=questions, tasks=task_info)

    elif request.method == "POST":
        answers = request.json["answers"]
        print(f"Received answers: {answers}")
        total_correct = 0
        total_questions = 0
        wrong_questions = {}

        for task in tasks:
            task_answers = {k: v for k, v in answers.items() if k.startswith(f"{task['unit']}_{task['type']}_")}
            result = flow_controller.handle_review(user_state, task, task_answers)
            print(f"Task {task}: Result {result}")
            total_correct += result["correct_count"]
            total_questions += result["question_count"]
            wrong_questions.update(result["wrong_questions"])

        correct_rate = total_correct / total_questions if total_questions > 0 else 0
        max_attempt = max(task["attempt"] for task in tasks)
        threshold = 0.6 if max_attempt <= 1 else 0.7 if max_attempt == 2 else 0.8
        print(f"Correct rate: {correct_rate}, Threshold: {threshold}, Total correct: {total_correct}, Total questions: {total_questions}")

        if "video_watched" in user_state and str(day) in user_state["video_watched"]:
            user_state["video_watched"][str(day)] = False
        user_manager.save_user(user_state)

        if correct_rate < threshold:
            print(f"Correct rate {correct_rate} < threshold {threshold}, redirecting to video")
            return jsonify({"next": "video", "user_id": user_id, "day": day})
        elif correct_rate < 1.0:
            print(f"Correct rate {correct_rate} < 1.0, redirecting to practice")
            return jsonify({"next": "practice", "user_id": user_id, "day": day})
        else:
            next_day = day + 1
            next_tasks = schedule_manager.get_tasks(next_day)
            print(f"Day {day} completed, next_day: {next_day}, next_tasks: {next_tasks}")

            if not next_tasks:
                if next_day > schedule_manager.schedule["combined"]:
                    user_state["progress"] = "completed"
                    user_manager.save_user(user_state)
                    print("Course completed")
                    return jsonify({"next": "done", "user_id": user_id})
                user_state["current_day"] = next_day
                user_manager.save_user(user_state)
                print("Rest day")
                return jsonify({"next": "rest", "user_id": user_id, "day": next_day})
            else:
                user_state["current_day"] = next_day
                user_manager.save_user(user_state)
                if any(task["attempt"] == 0 for task in next_tasks):
                    print("Next day is initial learning, redirecting to video")
                    return jsonify({"next": "video", "user_id": user_id, "day": next_day})
                print("Next day is quiz, redirecting to quiz")
                return jsonify({"next": "quiz", "user_id": user_id, "day": next_day})

@app.route("/practice/<user_id>/<int:day>", methods=["GET", "POST"])
def practice(user_id, day):
    user_state = user_manager.load_user(user_id)
    if not user_state or user_state["progress"] == "completed":
        return redirect(url_for("index"))

    tasks = schedule_manager.get_tasks(day)
    if request.method == "GET":
        questions = {}
        task_info = []
        has_wrong_questions = False
        for task in tasks:
            attempt = user_state["units"][task["unit"]][task["type"]]["attempts"][task["attempt"]]
            if attempt["correct_rate"] < 1.0 and any(attempt["wrong_questions"].values()):
                has_wrong_questions = True
                for subtype, q_list in attempt["wrong_questions"].items():
                    if q_list:
                        questions[subtype] = q_list
            task_info.append({"unit": task["unit"], "type": task["type"], "attempt": task["attempt"]})

        if not has_wrong_questions:
            if day == schedule_manager.schedule["combined"]:
                user_state["progress"] = "completed"
                user_manager.save_user(user_state)
                return redirect(url_for("index"))
            user_state["current_day"] += 1
            user_manager.save_user(user_state)
            return redirect(url_for("video", user_id=user_id, day=user_state["current_day"]))

        return render_template("practice.html", user_id=user_id, day=day, questions=questions, tasks=task_info)

    elif request.method == "POST":
        answers = request.json["answers"]
        all_correct = True
        for task in tasks:
            result = flow_controller.handle_practice(user_state, task, answers)
            if result["correct_count"] < result["question_count"]:
                all_correct = False
        user_manager.save_user(user_state)
        if all_correct:
            next_day = day + 1
            next_tasks = schedule_manager.get_tasks(next_day)
            if not next_tasks:
                if next_day > schedule_manager.schedule["combined"]:
                    user_state["progress"] = "completed"
                    user_manager.save_user(user_state)
                    return jsonify({"next": "done"})
                user_state["current_day"] = next_day
                user_manager.save_user(user_state)
                return jsonify({"next": "rest", "user_id": user_id, "day": next_day})
            else:
                user_state["current_day"] = next_day
                user_manager.save_user(user_state)
                if any(task["attempt"] == 0 for task in next_tasks):
                    return jsonify({"next": "video", "user_id": user_id, "day": next_day})
                return jsonify({"next": "quiz", "user_id": user_id, "day": next_day})
        return jsonify({"next": "practice", "user_id": user_id, "day": day})

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
    return render_template("rest.html", user_id=user_id, day=day)

@app.route("/done/<user_id>")
def done(user_id):
    return render_template("done.html", user_id=user_id)

if __name__ == "__main__":
    os.makedirs("static/videos", exist_ok=True)
    app.run(debug=True)
