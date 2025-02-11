import os
import shutil

def move_json_files(source_folder, target_folder):
    # 检查目标文件夹是否存在，如果不存在则创建
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    # 遍历源文件夹中的所有文件
    for filename in os.listdir(source_folder):
        # 检查文件是否是JSON文件
        if filename.endswith('.json'):
            # 构建源文件和目标文件的完整路径
            source_file = os.path.join(source_folder, filename)
            target_file = os.path.join(target_folder, filename)
            
            # 移动文件
            shutil.move(source_file, target_file)
            print(f"Moved: {source_file} -> {target_file}")

# 示例用法
source_folder = '/root/rag_project/data/qa'
target_folder = '/root/rag_project/data/qa/安徽合肥公共资源交易中心/政策'

move_json_files(source_folder, target_folder)