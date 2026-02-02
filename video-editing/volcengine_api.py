#!/usr/bin/env python3
"""火山引擎音视频识别API调用"""
import requests
import time
from config import VOLCENGINE_API_KEY, VOLCENGINE_APPID


class VolcEngineAPI:
    def __init__(self, api_key=None, app_id=None):
        self.api_key = api_key or VOLCENGINE_API_KEY
        self.app_id = app_id or VOLCENGINE_APPID
        self.base_url = "https://openspeech.bytedance.com/api/v1/vc"
        
    def transcribe_video(self, video_path):
        """上传视频并获取字幕"""
        print(f"📤 上传视频到火山引擎...")
        
        # 上传
        upload_url = f"{self.base_url}/submit"
        with open(video_path, 'rb') as f:
            files = {'data': f}
            headers = {'Authorization': f'Bearer {self.api_key}'}
            params = {
                'appid': self.app_id,
                'language': 'zh-CN',
                'use_itn': 'True'
            }
            
            response = requests.post(upload_url, files=files, headers=headers, params=params)
            result = response.json()
            
            if result.get('code') != 0:
                raise Exception(f"上传失败: {result.get('message')}")
            
            task_id = result['data']['id']
            print(f"✅ 上传成功，任务ID: {task_id}")
        
        # 轮询结果
        print(f"⏳ 等待识别...")
        query_url = f"{self.base_url}/query"
        
        while True:
            headers = {'Authorization': f'Bearer {self.api_key}'}
            params = {'appid': self.app_id, 'id': task_id}
            response = requests.get(query_url, headers=headers, params=params)
            result = response.json()
            
            if result.get('code') != 0:
                raise Exception(f"查询失败: {result.get('message')}")
            
            status = result['data']['status']
            
            if status == 'success':
                print(f"✅ 识别完成！")
                utterances = result['data']['utterances']
                subtitles = []
                for utt in utterances:
                    for word in utt.get('words', []):
                        subtitles.append({
                            'text': word['text'],
                            'start': word['start_time'] / 1000.0,
                            'end': word['end_time'] / 1000.0
                        })
                return subtitles
            elif status == 'failed':
                raise Exception(f"识别失败")
            elif status in ['running', 'queueing']:
                time.sleep(2)
            else:
                raise Exception(f"未知状态: {status}")
