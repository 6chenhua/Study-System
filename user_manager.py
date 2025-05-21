import json
import os
import shutil
import time
import traceback
import uuid

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
            },
            "video_watched": {}  # 初始化视频观看状态
        }
        UserManager.save_user(user_state)
        return user_state

    @staticmethod
    def load_user(user_id):
        file_path = f"user_state/{user_id}.json"
        backup_path = f"{file_path}.bak"
        temp_path = f"{file_path}.temp"
        
        # 检查并删除临时文件
        for path in [temp_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"删除旧的临时文件: {path}")
                except Exception as e:
                    print(f"无法删除临时文件 {path}: {str(e)}")
        
        # 优先尝试加载主文件
        user_state = None
        load_from_main = False
        
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip():  # 确保文件不为空
                        user_state = json.loads(content)
                        print(f"成功从主文件加载用户状态: {user_id}")
                        load_from_main = True
                    else:
                        print(f"主文件为空: {file_path}")
            except json.JSONDecodeError as e:
                print(f"主文件JSON解析错误 {user_id}: {str(e)}")
                print(traceback.format_exc())
            except Exception as e:
                print(f"加载主文件用户状态错误 {user_id}: {str(e)}")
                print(traceback.format_exc())
        
        # 如果主文件不存在或加载失败，尝试加载备份文件
        if not user_state and os.path.exists(backup_path):
            try:
                print(f"尝试从备份文件加载用户 {user_id}")
                with open(backup_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip():  # 确保文件不为空
                        user_state = json.loads(content)
                        # 如果成功从备份加载，立即同步到主文件
                        try:
                            with open(file_path, "w", encoding="utf-8") as mf:
                                mf.write(content)
                                print(f"已将备份数据同步到主文件")
                        except Exception as e:
                            print(f"同步备份到主文件失败: {str(e)}")
                    else:
                        print(f"备份文件为空: {backup_path}")
            except json.JSONDecodeError as e:
                print(f"备份文件JSON解析错误 {user_id}: {str(e)}")
            except Exception as e:
                print(f"从备份加载用户状态错误 {user_id}: {str(e)}")
                print(traceback.format_exc())
        
        # 加载成功后，检查是否需要从备份恢复视频观看状态
        if user_state and load_from_main and os.path.exists(backup_path):
            try:
                with open(backup_path, "r", encoding="utf-8") as bf:
                    backup_content = bf.read()
                    if backup_content.strip():  # 确保备份文件不为空
                        backup_state = json.loads(backup_content)
                        # 检查视频观看状态是否在备份中存在且比主文件更新
                        if "video_watched" in backup_state and backup_state["video_watched"]:
                            main_video_watched = user_state.get("video_watched", {})
                            backup_video_watched = backup_state.get("video_watched", {})
                            
                            # 检查备份中是否有主文件中没有的天数记录
                            updated = False
                            for day, watched in backup_video_watched.items():
                                if watched and (day not in main_video_watched or not main_video_watched[day]):
                                    print(f"发现备份文件中有更新的视频观看状态: day={day}, watched={watched}")
                                    if "video_watched" not in user_state:
                                        user_state["video_watched"] = {}
                                    user_state["video_watched"][day] = watched
                                    updated = True
                            
                            if updated:
                                # 发现更新，保存回主文件
                                UserManager.save_user(user_state)
                                print(f"已从备份文件恢复视频观看状态到主文件")
            except json.JSONDecodeError as e:
                print(f"检查备份文件JSON解析错误: {str(e)}")
            except Exception as e:
                print(f"检查备份文件时出错: {str(e)}")
        
        # 确保返回的用户状态包含必要的字段
        if user_state:
            if "video_watched" not in user_state:
                user_state["video_watched"] = {}
                print(f"为用户 {user_id} 添加缺失的video_watched字段")
            return user_state
        
        return None

    @staticmethod
    def save_user(user_state):
        try:
            # 检查用户状态是否有效
            if not user_state or not isinstance(user_state, dict) or "user_id" not in user_state:
                print("保存用户状态失败: 无效的用户状态")
                return False
                
            # 创建用户状态目录
            os.makedirs("user_state", exist_ok=True)
            
            # 保存用户状态
            user_id = user_state["user_id"]
            file_path = f"user_state/{user_id}.json"
            backup_path = f"{file_path}.bak"
            temp_path = f"{file_path}.temp"
            
            # 确保有视频观看状态字段
            if "video_watched" not in user_state:
                user_state["video_watched"] = {}
                print(f"为用户 {user_id} 添加缺失的video_watched字段")
            
            print(f"正在保存用户状态，视频观看状态: {user_state.get('video_watched', {})}")
            
            # 转换为JSON字符串
            try:
                json_str = json.dumps(user_state, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"JSON序列化失败: {str(e)}")
                return False
            
            # 使用不同的保存策略
            save_success = False
            
            # 策略1: 直接保存到备份文件
            try:
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(json_str)
                    f.flush()
                    os.fsync(f.fileno())
                print(f"成功保存到备份文件: {backup_path}")
                save_success = True
            except Exception as e:
                print(f"保存到备份文件失败: {str(e)}")
            
            # 策略2: 使用临时文件然后重命名
            try:
                # 生成唯一的临时文件名避免冲突
                unique_temp = f"{temp_path}.{uuid.uuid4().hex}"
                with open(unique_temp, "w", encoding="utf-8") as f:
                    f.write(json_str)
                    f.flush()
                    os.fsync(f.fileno())
                
                # 确保目标文件不存在（Windows特殊处理）
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"移除现有文件失败: {str(e)}")
                
                # 重命名临时文件
                shutil.move(unique_temp, file_path)
                print(f"成功保存到主文件(通过临时文件): {file_path}")
                save_success = True
            except Exception as e:
                print(f"通过临时文件保存失败: {str(e)}")
                # 如果临时文件策略失败，尝试直接写入
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(json_str)
                        f.flush()
                        os.fsync(f.fileno())
                    print(f"成功直接保存到主文件: {file_path}")
                    save_success = True
                except Exception as e2:
                    print(f"直接保存到主文件失败: {str(e2)}")
            
            # 验证文件是否成功保存
            saved_video_watched = None
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        saved_data = json.load(f)
                        saved_video_watched = saved_data.get("video_watched", {})
                        print(f"验证保存的视频观看状态: {saved_video_watched}")
                except Exception as e:
                    print(f"验证保存内容时出错: {str(e)}")
            
            # 如果主文件验证失败但备份存在，尝试从备份恢复
            if (not saved_video_watched or saved_video_watched != user_state.get("video_watched", {})) and os.path.exists(backup_path):
                try:
                    print("主文件保存验证失败，尝试从备份恢复")
                    with open(backup_path, "r", encoding="utf-8") as bf:
                        backup_content = bf.read()
                    with open(file_path, "w", encoding="utf-8") as mf:
                        mf.write(backup_content)
                        mf.flush()
                        os.fsync(mf.fileno())
                    print("已从备份恢复到主文件")
                except Exception as e:
                    print(f"从备份恢复主文件失败: {str(e)}")
            
            return save_success
                
        except Exception as e:
            print(f"保存用户状态错误: {str(e)}")
            print(traceback.format_exc())
            return False

    @staticmethod
    def force_save_video_watched(user_id, day, watched=True):
        """强制保存视频观看状态，适用于其他方法失败的情况"""
        try:
            # 加载用户状态
            user_state = UserManager.load_user(user_id)
            if not user_state:
                print(f"强制保存失败: 用户 {user_id} 不存在")
                return False
            
            # 设置视频观看状态
            if "video_watched" not in user_state:
                user_state["video_watched"] = {}
            
            user_state["video_watched"][str(day)] = watched
            print(f"强制设置视频观看状态: user_id={user_id}, day={day}, watched={watched}")
            
            # 直接写入文件
            file_path = f"user_state/{user_id}.json"
            json_str = json.dumps(user_state, ensure_ascii=False, indent=4)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_str)
                f.flush()
                os.fsync(f.fileno())
            
            print(f"强制保存视频观看状态成功")
            return True
        except Exception as e:
            print(f"强制保存视频观看状态失败: {str(e)}")
            print(traceback.format_exc())
            return False
