import os
import json
from PIL import Image, UnidentifiedImageError
from tqdm import tqdm

def process_and_organize_images(source_dir, output_dir, max_dimension, jpg_quality):
    """
    处理源目录下的图片，保留其子目录结构（如 horizontal/vertical），
    并对每个子目录生成一个 manifest.json 文件。

    :param source_dir: 包含原始图片的源目录 (e.g., 'pixiv_images')
    :param output_dir: 处理后图片的输出目录 (e.g., 'api_ready_images')
    :param max_dimension: 图片最长边的最大像素值，None表示不调整尺寸
    :param jpg_quality: 输出JPEG图片的质量 (1-95)
    """
    
    # 1. 检查源目录
    if not os.path.isdir(source_dir):
        print(f"错误：源目录 '{source_dir}' 不存在。")
        return

    print("--- 开始按分类处理图片 ---")
    
    # 2. 遍历源目录中的每个 "标签" 文件夹 (e.g., '古明地こいし')
    for tag_name in os.listdir(source_dir):
        tag_path = os.path.join(source_dir, tag_name)
        if not os.path.isdir(tag_path):
            continue

        print(f"\n正在处理标签: '{tag_name}'")
        output_tag_path = os.path.join(output_dir, tag_name)
        
        # 3. 遍历每个 "分类" 文件夹 (e.g., 'horizontal', 'vertical', 'square')
        for category_name in os.listdir(tag_path):
            category_path = os.path.join(tag_path, category_name)
            if not os.path.isdir(category_path):
                continue

            print(f"  - 处理分类: '{category_name}'")
            output_category_path = os.path.join(output_tag_path, category_name)
            os.makedirs(output_category_path, exist_ok=True)
            
            # 搜集当前分类下的所有图片
            source_files = [
                os.path.join(category_path, f) 
                for f in os.listdir(category_path) 
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
            ]
            
            if not source_files:
                print(f"    在 '{category_name}' 中未找到图片，跳过。")
                continue

            # 4. 处理并保存图片
            processed_filenames = []
            pbar = tqdm(source_files, desc=f"    {category_name}", leave=False)
            for file_path in pbar:
                try:
                    img = Image.open(file_path)
                    if img.mode in ('RGBA', 'P', 'LA'):
                        img = img.convert('RGB')

                    if max_dimension and (img.width > max_dimension or img.height > max_dimension):
                        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

                    base_name, _ = os.path.splitext(os.path.basename(file_path))
                    output_filename = f"{base_name}.jpg"
                    output_file_path = os.path.join(output_category_path, output_filename)

                    img.save(output_file_path, 'JPEG', quality=jpg_quality, optimize=True)
                    processed_filenames.append(output_filename)

                except UnidentifiedImageError:
                    print(f"\n    警告：无法识别的文件，已跳过: {file_path}")
                except Exception as e:
                    print(f"\n    处理文件 {file_path} 时出错: {e}")

            # 5. 为当前分类创建 manifest.json
            if processed_filenames:
                manifest_path = os.path.join(output_category_path, "manifest.json")
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_filenames, f) # 使用更紧凑的格式
                print(f"    完成！处理了 {len(processed_filenames)} 张图片，索引保存至 {manifest_path}")

if __name__ == '__main__':
    # ==================== 配置区域 ====================
    SOURCE_ROOT_DIR = "pixiv_images"
    OUTPUT_DIR = "api_ready_images"
    MAX_DIMENSION = 1920
    JPG_QUALITY = 25
    # ===============================================

    process_and_organize_images(
        source_dir=SOURCE_ROOT_DIR,
        output_dir=OUTPUT_DIR,
        max_dimension=MAX_DIMENSION,
        jpg_quality=JPG_QUALITY
    )
    
    print("\n所有任务完成！")