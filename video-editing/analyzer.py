#!/usr/bin/env python3
"""口误分析器"""
from config import MIN_SILENCE_DURATION, FILLER_WORDS, PAUSE_WORDS


class VideoAnalyzer:
    """视频内容分析器"""
    
    def __init__(self, subtitles):
        self.subtitles = subtitles
        self.segments_to_remove = []
        
    def analyze(self):
        """分析所有需要删除的片段"""
        print("🔍 分析口误片段...")
        
        self._find_silence()
        self._find_filler_words()
        self._find_repetitions()
        self._merge_segments()
        
        print(f"✅ 分析完成！发现 {len(self.segments_to_remove)} 个需要删除的片段")
        return self.segments_to_remove
    
    def _find_silence(self):
        """识别静音片段"""
        for i in range(len(self.subtitles) - 1):
            curr = self.subtitles[i]
            next_sub = self.subtitles[i + 1]
            gap = next_sub['start'] - curr['end']
            
            if gap >= MIN_SILENCE_DURATION:
                self.segments_to_remove.append({
                    'start': curr['end'],
                    'end': next_sub['start'],
                    'reason': '静音',
                    'confidence': 1.0
                })
    
    def _find_filler_words(self):
        """识别卡顿词和语气词"""
        for sub in self.subtitles:
            text = sub['text'].strip()
            
            # 卡顿词
            if text in FILLER_WORDS:
                self.segments_to_remove.append({
                    'start': sub['start'],
                    'end': sub['end'],
                    'reason': f'卡顿词: {text}',
                    'confidence': 0.9
                })
            
            # 语气词
            if text in PAUSE_WORDS:
                self.segments_to_remove.append({
                    'start': sub['start'],
                    'end': sub['end'],
                    'reason': f'语气词: {text}',
                    'confidence': 0.85
                })
    
    def _find_repetitions(self):
        """识别重复句"""
        for i in range(len(self.subtitles) - 1):
            curr_text = self.subtitles[i]['text']
            next_text = self.subtitles[i + 1]['text']
            
            if curr_text == next_text and len(curr_text) > 2:
                self.segments_to_remove.append({
                    'start': self.subtitles[i + 1]['start'],
                    'end': self.subtitles[i + 1]['end'],
                    'reason': f'重复: {curr_text}',
                    'confidence': 0.95
                })
    
    def _merge_segments(self):
        """合并相邻的删除片段"""
        if not self.segments_to_remove:
            return
        
        self.segments_to_remove.sort(key=lambda x: x['start'])
        merged = [self.segments_to_remove[0]]
        
        for seg in self.segments_to_remove[1:]:
            last = merged[-1]
            if seg['start'] - last['end'] < 0.5:  # 相隔0.5秒内合并
                last['end'] = seg['end']
                last['reason'] += f" + {seg['reason']}"
            else:
                merged.append(seg)
        
        self.segments_to_remove = merged
