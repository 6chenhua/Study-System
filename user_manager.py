import json
import os

class UserManager:
    @staticmethod
    def init_user(user_id, style):
        user_state = {
            "user_id": user_id,
            "style": style,
            "current_day": 1,
            "progress": "started",
            "units": {
                "unit1": {
                    "word": {"attempts": []},
                    "sentence": {"attempts": []}
                },
                "unit2": {
                    "word": {"attempts": []},
                    "sentence": {"attempts": []}
                }
            }
        }
        UserManager.save_user(user_state)
        return user_state

    @staticmethod
    def load_user(user_id):
        file_path = f"user_state/{user_id}.json"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    @staticmethod
    def save_user(user_state):
        os.makedirs("user_state", exist_ok=True)
        file_path = f"user_state/{user_state['user_id']}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(user_state, f, ensure_ascii=False, indent=4)
