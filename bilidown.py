import requests
import json
import re
import os
import argparse
from urllib.parse import urlparse, parse_qs
from tqdm import tqdm

class BilibiliCrawler:
    def __init__(self):
        """初始化爬虫"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_bv_from_url(self, url):
        """从URL中提取BV号"""
        parsed_url = urlparse(url)
        path = parsed_url.path
        bv_match = re.search(r'BV[0-9A-Za-z]+', path)
        if bv_match:
            return bv_match.group()
        return None
    
    def get_video_info(self, bv):
        """获取视频信息"""
        try:
            url = f"https://www.bilibili.com/video/{bv}"
            response = self.session.get(url)
            response.raise_for_status()
            
            # 提取视频信息
            title_match = re.search(r'<title>(.*?)</title>', response.text)
            title = title_match.group(1).replace('_哔哩哔哩_bilibili', '') if title_match else f"视频_{bv}"
            
            # 提取视频数据
            initial_state_match = re.search(r'window\.__INITIAL_STATE__=(.*?);\(function\(', response.text)
            if initial_state_match:
                initial_state = json.loads(initial_state_match.group(1))
                # 提取视频链接
                if 'videoData' in initial_state and 'pages' in initial_state['videoData']:
                    pages = initial_state['videoData']['pages']
                    return {
                        'title': title,
                        'pages': pages
                    }
            
            # 如果没有找到初始状态，尝试其他方式
            video_info_match = re.search(r'__playinfo__=(.*?)</script>', response.text)
            if video_info_match:
                video_info = json.loads(video_info_match.group(1))
                return {
                    'title': title,
                    'video_info': video_info
                }
            
            return None
        except Exception as e:
            print(f"获取视频信息失败: {e}")
            return None
    
    def download_video(self, url, filename):
        """下载视频"""
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            with open(filename, 'wb') as f, tqdm(
                desc=filename,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for data in response.iter_content(chunk_size=1024):
                    size = f.write(data)
                    bar.update(size)
            return True
        except Exception as e:
            print(f"下载视频失败: {e}")
            return False
    
    def crawl(self, url, output_dir='downloads'):
        """主爬取函数"""
        # 获取BV号
        bv = self.get_bv_from_url(url)
        if not bv:
            print("无法从URL中提取BV号")
            return
        
        # 获取视频信息
        video_info = self.get_video_info(bv)
        if not video_info:
            print("无法获取视频信息")
            return
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 处理视频
        if 'pages' in video_info:
            for page in video_info['pages']:
                cid = page['cid']
                page_title = page.get('part', f"P{page['page']}")
                
                # 获取视频链接
                api_url = f"https://api.bilibili.com/x/player/playurl?bvid={bv}&cid={cid}&qn=80&type=&otype=json"
                response = self.session.get(api_url)
                play_info = response.json()
                
                if 'data' in play_info and 'durl' in play_info['data']:
                    for durl in play_info['data']['durl']:
                        video_url = durl['url']
                        filename = os.path.join(output_dir, f"{video_info['title']}_{page_title}.mp4")
                        print(f"正在下载: {filename}")
                        self.download_video(video_url, filename)
        elif 'video_info' in video_info:
            # 处理其他格式的视频信息
            if 'data' in video_info['video_info'] and 'durl' in video_info['video_info']['data']:
                for durl in video_info['video_info']['data']['durl']:
                    video_url = durl['url']
                    filename = os.path.join(output_dir, f"{video_info['title']}.mp4")
                    print(f"正在下载: {filename}")
                    self.download_video(video_url, filename)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='B站视频爬虫')
    parser.add_argument('url', help='B站视频URL')
    parser.add_argument('--output', '-o', default='downloads', help='输出目录')
    args = parser.parse_args()
    
    crawler = BilibiliCrawler()
    crawler.crawl(args.url, args.output)

if __name__ == '__main__':
    main()
