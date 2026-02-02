#!/usr/bin/env python3
"""视频剪辑执行"""
import subprocess
import os


class VideoEditor:
    """视频剪辑器"""
    
    def __init__(self, video_path):
        self.video_path = video_path
        self.output_path = self._get_output_path()
        
    def _get_output_path(self):
        """生成输出文件路径"""
        basename = os.path.basename(self.video_path)
        name, ext = os.path.splitext(basename)
        return os.path.join('output', f"{name}_cut{ext}")
    
    def cut(self, segments_to_remove):
        """
        剪辑视频，删除指定片段
        
        Args:
            segments_to_remove: 要删除的片段列表 [{'start': 1.2, 'end': 3.4}, ...]
        """
        if not segments_to_remove:
            print("⚠️  没有需要删除的片段")
            return self.video_path
        
        print(f"✂️  开始剪辑，删除 {len(segments_to_remove)} 个片段...")
        
        # 计算保留的片段
        keep_segments = self._calculate_keep_segments(segments_to_remove)
        
        if not keep_segments:
            print("❌ 没有需要保留的内容")
            return None
        
        # 使用ffmpeg合并保留的片段
        self._merge_segments(keep_segments)
        
        print(f"✅ 剪辑完成！")
        print(f"📁 输出文件: {self.output_path}")
        return self.output_path
    
    def _calculate_keep_segments(self, remove_segments):
        """计算需要保留的片段"""
        # 获取视频总时长
        duration = self._get_video_duration()
        
        # 按时间排序删除片段
        remove_segments = sorted(remove_segments, key=lambda x: x['start'])
        
        keep_segments = []
        current_time = 0.0
        
        for seg in remove_segments:
            if current_time < seg['start']:
                keep_segments.append({
                    'start': current_time,
                    'end': seg['start']
                })
            current_time = seg['end']
        
        # 最后一段
        if current_time < duration:
            keep_segments.append({
                'start': current_time,
                'end': duration
            })
        
        return keep_segments
    
    def _get_video_duration(self):
        """获取视频时长"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            self.video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    
    def _merge_segments(self, keep_segments):
        """使用ffmpeg合并片段"""
        # 创建临时分段文件
        segment_files = []
        
        for i, seg in enumerate(keep_segments):
            segment_file = f"output/temp_seg_{i}.mp4"
            segment_files.append(segment_file)
            
            # 提取片段
            duration = seg['end'] - seg['start']
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(seg['start']),
                '-t', str(duration),
                '-i', self.video_path,
                '-c', 'copy',
                segment_file
            ]
            subprocess.run(cmd, capture_output=True)
        
        # 合并所有片段
        concat_file = 'output/concat_list.txt'
        with open(concat_file, 'w') as f:
            for seg_file in segment_files:
                f.write(f"file '{os.path.abspath(seg_file)}'\n")
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            self.output_path
        ]
        subprocess.run(cmd, capture_output=True)
        
        # 清理临时文件
        for seg_file in segment_files:
            os.remove(seg_file)
        os.remove(concat_file)
