import os
import re
import time
import requests
from urllib.parse import urlparse, unquote, quote
from tqdm import tqdm

class PixivScraper:
    def __init__(self, cookie, save_path='downloads', sort_by_orientation=True, exclude_manga=True):
        """
        初始化爬虫
        :param cookie: 从浏览器获取的 Pixiv Cookie
        :param save_path: 图片保存的根目录
        :param sort_by_orientation: 是否按横/竖图/方图分类保存
        :param exclude_manga: 是否排除漫画，只下载单张插画
        """
        if not cookie:
            raise ValueError("Cookie 不能为空，请提供有效的 Pixiv Cookie。")
            
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Cookie': cookie,
            'Referer': 'https://www.pixiv.net/'
        })
        self.save_path = save_path
        self.sort_by_orientation = sort_by_orientation
        self.exclude_manga = exclude_manga
        self.artwork_id_pattern = re.compile(r'^(\d+)_p\d+\..+$')

    def _make_request(self, url, params=None, retries=3, timeout=15):
        """封装的请求方法，包含重试逻辑"""
        for i in range(retries):
            try:
                response = self.session.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"请求失败: {e}。第 {i + 1}/{retries} 次重试...")
                time.sleep(3)
        print(f"请求 {url} 失败，已达到最大重试次数。")
        return None

    def fetch_artwork_ids_from_tag(self, tag, limit=500):
        """根据标签搜索作品，按热度排序"""
        search_type = "插画" if self.exclude_manga else "所有作品"
        print(f"正在搜索标签: '{tag}'，目标数量: {limit} ({search_type})")
        
        all_artwork_ids = []
        page = 1
        pbar = tqdm(total=limit, desc="搜索作品ID")
        encoded_tag = quote(tag)
        
        while len(all_artwork_ids) < limit:
            search_url = f"https://www.pixiv.net/ajax/search/artworks/{encoded_tag}"
            params = {
                'word': tag, 'order': 'popular_d', 'mode': 'all', 'p': page,
                's_mode': 's_tag_full', 'type': 'all', 'lang': 'zh'
            }
            data = self._make_request(search_url, params=params)
            
            if not data or data.get('error') or not data.get('body', {}).get('illustManga', {}).get('data'):
                print("\n没有找到更多作品，或API返回错误。搜索提前结束。")
                break

            artworks = data['body']['illustManga']['data']
            if not artworks:
                print("\n当前页没有作品，搜索结束。")
                break

            for art in artworks:
                is_illustration = (art.get('illustType') == 0)
                if self.exclude_manga and not is_illustration:
                    continue

                if len(all_artwork_ids) < limit:
                    all_artwork_ids.append(art['id'])
                    pbar.update(1)
                else:
                    break
            
            if len(all_artwork_ids) >= limit:
                break
                
            page += 1
            time.sleep(1)

        pbar.close()
        print(f"搜索完成，共找到 {len(all_artwork_ids)} 个符合条件的作品ID。")
        return all_artwork_ids

    def get_image_details(self, artwork_id):
        """获取单个作品的所有图片详情 (URL, width, height)"""
        pages_url = f"https://www.pixiv.net/ajax/illust/{artwork_id}/pages"
        data = self._make_request(pages_url)
        if not data or data.get('error'):
            print(f"获取作品 {artwork_id} 的图片详情失败。")
            return []
        return [{'url': p['urls']['original'], 'width': p['width'], 'height': p['height']} for p in data['body']]

    def download_image(self, url, folder_path, artwork_id):
        """下载单张图片"""
        try:
            os.makedirs(folder_path, exist_ok=True)
            parsed_url = urlparse(url)
            filename = os.path.basename(unquote(parsed_url.path))
            filepath = os.path.join(folder_path, filename)
            
            if os.path.exists(filepath):
                return

            headers = self.session.headers.copy()
            headers['Referer'] = f'https://www.pixiv.net/artworks/{artwork_id}'
            response = self.session.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        except requests.exceptions.RequestException as e:
            print(f"下载图片 {url} 失败: {e}")
        except Exception as e:
            print(f"处理图片 {url} 时发生未知错误: {e}")

    def _get_existing_artwork_ids(self, directories):
        """扫描指定目录列表，从文件名中提取并返回所有已存在的作品ID。"""
        existing_ids = set()
        print("正在扫描本地文件，查找已下载的作品...")
        for directory in directories:
            if not os.path.exists(directory):
                continue
            for filename in os.listdir(directory):
                match = self.artwork_id_pattern.match(filename)
                if match:
                    existing_ids.add(match.group(1))
        
        if existing_ids:
            print(f"扫描完成，发现 {len(existing_ids)} 个已下载过的作品ID。")
        else:
            print("未在本地发现已下载的作品。")
        return existing_ids

    def run(self, tag, limit=500):
        """主执行函数"""
        safe_folder_name = re.sub(r'[\\/*?:"<>|]', "", tag)
        base_path = os.path.join(self.save_path, safe_folder_name)
        
        all_possible_dirs = []
        if self.sort_by_orientation:
            horizontal_dir, vertical_dir, square_dir = [os.path.join(base_path, d) for d in ['horizontal', 'vertical', 'square']]
            all_possible_dirs.extend([horizontal_dir, vertical_dir, square_dir])
            print(f"图片将分类保存到: {base_path} 下的子文件夹")
        else:
            all_possible_dirs.append(base_path)
            os.makedirs(base_path, exist_ok=True)
            print(f"图片将保存到: {base_path}")

        existing_ids = self._get_existing_artwork_ids(all_possible_dirs)
        
        artwork_ids = self.fetch_artwork_ids_from_tag(tag, limit)
        if not artwork_ids: return

        ids_to_download = [pid for pid in artwork_ids if str(pid) not in existing_ids]

        print("-" * 30)
        print(f"总共获取 {len(artwork_ids)} 个作品ID。")
        print(f"其中 {len(ids_to_download)} 个是新的，将被下载。")
        print(f"{len(existing_ids)} 个已存在，将被跳过。")
        print("-" * 30)
        
        if not ids_to_download:
            print("\n所有目标作品均已下载，无需任何操作。")
            return

        for artwork_id in tqdm(ids_to_download, desc="下载新作品"):
            image_details = self.get_image_details(artwork_id)
            if not image_details: continue

            for detail in image_details:
                target_path = base_path
                if self.sort_by_orientation:
                    if detail['width'] > detail['height']: target_path = horizontal_dir
                    elif detail['height'] > detail['width']: target_path = vertical_dir
                    else: target_path = square_dir
                
                self.download_image(detail['url'], target_path, artwork_id)
                time.sleep(0.1)
            time.sleep(0.3)
        print("\n所有新作品下载完成！")

# <--- 补回这个被遗漏的函数
def get_tag_from_url(url):
    """从 Pixiv Tag URL 中提取标签名"""
    match = re.search(r'/tags/([^/]+)/artworks', url)
    return unquote(match.group(1)) if match else None

if __name__ == '__main__':
    # ==================== 配置区域 ====================
    # 1. 在这里粘贴你从浏览器复制的Cookie
    MY_COOKIE = "p_ab_id=7; p_ab_id_2=3; p_ab_d_id=1213592852; device_token=dea402ea398c802e025f05cd5303e750; privacy_policy_agreement=7; c_type=25; privacy_policy_notification=0; a_type=0; b_type=2; _gcl_au=1.1.571192103.1751097653; __utmc=235335808; __utmz=235335808.1753155267.6.5.utmcsr=pixiv.help|utmccn=(referral)|utmcmd=referral|utmcct=/; cto_bundle=M0kZJ19UclYwcUpJMSUyRm92ZHphUXZxU2xiWGYyaGxlM3R3NkdWQTFQZCUyRkRCSjI5N0JBRlZiOUtQNHJjWWMxYmYlMkZRYUNiMVpUczVBS0R4WW40SVNZczlkMUF5Qkt3d2hLN0ZDSDJQem1NMUhremVCdGJYdXMlMkI1WnlUWkdEYzNHTDR1R3NUYnVGTCUyQlFJdUV5UWVjNThzMXZHRFRRJTNEJTNE; _gid=GA1.2.2134769710.1753155667; cc1=2025-07-22%2013%3A15%3A10; __utma=235335808.1983970885.1751097449.1753155267.1753157711.7; cf_clearance=jdOB5JrkYaRyHYt1J5SFS36SY.OtXVRs96cHG4WhOMA-1753157713-1.2.1.1-KVmy0j.VT0R2KljwtWwpygck_4S2AqS18NAZUC._.sWEPImKYxsCnZvjF7KdpJEGVie10hJWDhxB9UTV5O9aAHuZ6ezvZMMSn0omVcoDpB6qeAR4DM15gHOya_fjg07Lu8yd.RI.Lwh96ZwKWS9sknJLG.ENtzYDH551Rg5pVOOx2hraERE.4_XzmjzYWaKm.mYjZ5bsxRhKy6Zh.BeActwW..e9wn1u7ntuZMz.ra8; _ga=GA1.1.1784064843.1751097449; PHPSESSID=110190308_hAKVFug3xztpRkw5Qcy0RFsKPOaEYhzN; _ga_MZ1NL4PHH0=GS2.1.s1753157714$o2$g1$t1753157876$j8$l0$h0; FCNEC=%5B%5B%22AKsRol82FBjsK-kwqq4S1VkrfaPH2jJmDj4NeXg2nRhyVEnE4vjIac9qbyUAj6T08UROr90XLTTjhYH5xw6MMzyvNlUB-R-oXrF7Q9byU9LrZGnslfJF4CCqvuoVHTNiHQvd2JfXrD3o3R1yrepeO11JPULWj32P1Q%3D%3D%22%5D%5D; __cf_bm=acaXZRSxy4sq3eK7kKBfaw3fRllYvNPyqW.ILiBR0m4-1753158340-1.0.1.1-b.RpsctG8BsO6RTByehFnwO4jMrhuzXxuKP3PMgVcsf2A6PkXt90kV8zNxIa9BFhYLJt0hj40aOmJwMdrohaONGjqlo3WvnhxpaCyHJ_NVRro869OaQyVBnWWgozP1sE; _cfuvid=HQCtsB9mbtLGkVu4xjZIwgJR7P2Ctj80Py.cMJ.oLt8-1753158340307-0.0.1.1-604800000; _ga_75BBYNYN9J=GS2.1.s1753155266$o9$g1$t1753158338$j60$l0$h0; __utmv=235335808.|2=login%20ever=yes=1^3=plan=premium=1^5=gender=female=1^6=user_id=110190308=1^9=p_ab_id=7=1^10=p_ab_id_2=3=1^11=lang=zh=1^20=webp_available=yes=1; __utmt=1; __utmb=235335808.14.10.1753157711" 
    
    # 2. 【推荐】在这里粘贴完整的Tag页面URL
    TARGET_URL = "https://www.pixiv.net/tags/%E5%8F%A4%E6%98%8E%E5%9C%B0%E3%81%93%E3%81%84%E3%81%97/artworks?order=popular_d"
    
    # 3. 【备用】如果不想用URL，也可以在这里直接指定标签名
    TARGET_TAG = ""
    
    # 4. 设置是否排除漫画，只下载单张插画
    EXCLUDE_MANGA = True
    
    # 5. 设置是否按横/竖图分类
    SORT_BY_ORIENTATION = True
    
    # 6. 设置下载作品的数量
    DOWNLOAD_LIMIT = 500
    
    # 7. 设置图片保存的根目录
    SAVE_DIRECTORY = "pixiv_images"
    # ===============================================

    final_tag = get_tag_from_url(TARGET_URL) if TARGET_URL else TARGET_TAG

    if not final_tag: 
        print("错误：目标标签未指定。请设置 'TARGET_URL' 或 'TARGET_TAG'。")
    else:
        try:
            scraper = PixivScraper(
                cookie=MY_COOKIE, 
                save_path=SAVE_DIRECTORY,
                sort_by_orientation=SORT_BY_ORIENTATION,
                exclude_manga=EXCLUDE_MANGA
            )
            scraper.run(tag=final_tag, limit=DOWNLOAD_LIMIT)
        except ValueError as ve: 
            print(ve)
        except Exception as e: 
            print(f"发生了一个意料之外的错误: {e}")