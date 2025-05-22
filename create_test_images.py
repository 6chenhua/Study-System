import os
import shutil

# 确保目标目录存在
target_dir = "static/images/questions"
os.makedirs(target_dir, exist_ok=True)

# 复制现有图片文件来创建新的图片文件
source_files = ["book.png", "pencil.png"]
target_files = ["ruler.png", "eraser.png"]

for source_file in source_files:
    source_path = os.path.join(target_dir, source_file)
    if os.path.exists(source_path):
        # 复制第一个源文件创建缺少的目标文件
        for target_file in target_files:
            target_path = os.path.join(target_dir, target_file)
            if not os.path.exists(target_path):
                print(f"创建图片文件: {target_path}")
                shutil.copy(source_path, target_path)

print("所有测试图片已创建完成") 