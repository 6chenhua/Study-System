import os
import requests

# 确保目标目录存在
target_dir = "static/images/questions"
os.makedirs(target_dir, exist_ok=True)

# 定义图片URL和本地文件名
image_urls = {
    "cat.jpg": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?q=80&w=800&h=600&auto=format&fit=crop",
    "dog1.jpg": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?q=80&w=800&h=600&auto=format&fit=crop",
    "dog2.jpg": "https://images.unsplash.com/photo-1587300003388-59208cc962cb?q=80&w=800&h=600&auto=format&fit=crop",
    "dog3.jpg": "https://images.unsplash.com/photo-1561037404-61cd46aa615b?q=80&w=800&h=600&auto=format&fit=crop"
}

# 下载图片
for filename, url in image_urls.items():
    target_path = os.path.join(target_dir, filename)
    
    # 只下载不存在的图片
    if not os.path.exists(target_path):
        print(f"下载图片: {filename} 从 {url}")
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"成功下载: {filename}")
        except Exception as e:
            print(f"下载失败: {filename} - {str(e)}")
    else:
        print(f"跳过已存在的图片: {filename}")

print("图片下载完成！") 