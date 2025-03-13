import json

class ScheduleManager:
    def __init__(self):
        with open("data/schedule.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            self.schedule = data["schedule"]
            self.subtype_schedule = data["subtype_schedule"]

    def get_tasks(self, day):
        tasks = []
        # 优先检查是否是休息日
        if day in self.schedule["rest"]:
            return []  # 休息日，无任务

        # 处理学习和复习任务
        for unit in self.schedule:
            if unit == "combined" and day == self.schedule["combined"]:
                tasks.append({
                    "unit": "combined",
                    "type": "all",
                    "attempt": 0,
                    "subtypes": self.subtype_schedule[str(day)]["word"] + self.subtype_schedule[str(day)]["sentence"]
                })
            elif unit != "combined" and unit != "rest":  # 排除 "rest"
                for content_type, days in self.schedule[unit].items():
                    if day in days:
                        attempt = days.index(day)
                        subtypes = self.subtype_schedule[str(day)][content_type]
                        tasks.append({
                            "unit": unit,
                            "type": content_type,
                            "attempt": attempt,
                            "subtypes": subtypes
                        })
        return tasks
