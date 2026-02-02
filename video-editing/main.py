#!/usr/bin/env python3
"""
AI视频粗剪工具 - 主程序

使用方法:
    python main.py your_video.mp4
"""
import sys
import os
from volcengine_api import VolcEngineAPI
from analyzer import VideoAnalyzer
from web_server import start_server, wait_for_confirmation
from editor import VideoEditor
from config import WEB_SERVER_PORT


def main():
    if len(sys.argv) < 2:
        print("使用方法: python main.py <video_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    if not os.path.exists(video_path):
        print(f"❌ 文件不存在: {video_path}")
        sys.exit(1)
    
    print(f"🎬 开始处理视频: {video_path}")
    print()
    
    # 第一步：调用火山引擎API识别字幕
    api = VolcEngineAPI()
    subtitles = api.transcribe_video(video_path)
    print(f"📝 识别到 {len(subtitles)} 个词")
    print()
    
    # 第二步：分析口误片段
    analyzer = VideoAnalyzer(subtitles)
    segments_to_remove = analyzer.analyze()
    print()
    
    if not segments_to_remove:
        print("✨ 没有发现需要删除的片段！视频已经很紧凑了")
        return
    
    # 第三步：启动审核界面
    print("🌐 启动审核界面...")
    start_server(video_path, subtitles, segments_to_remove, port=WEB_SERVER_PORT)
    
    print(f"✅ 审核界面已启动！")
    print(f"📱 请在浏览器打开: http://localhost:{WEB_SERVER_PORT}")
    print()
    print("💡 提示:")
    print("  - Shift + 点击片段可选中/取消")
    print("  - 审核完成后点击\"确认并剪辑\"")
    print()
    
    # 第四步：等待用户审核
    confirmed_segments = wait_for_confirmation()
    print()
    print(f"✅ 用户确认删除 {len(confirmed_segments)} 个片段")
    print()
    
    # 第五步：执行剪辑
    editor = VideoEditor(video_path)
    output_path = editor.cut(confirmed_segments)
    
    if output_path:
        print()
        print("=" * 50)
        print("🎉 完成！")
        print(f"📁 输出文件: {output_path}")
        print("=" * 50)
    else:
        print("❌ 剪辑失败")


if __name__ == '__main__':
    main()
