#!/usr/bin/env python3
"""审核界面Web服务"""
from flask import Flask, render_template_string, jsonify, request
import threading
import json


app = Flask(__name__)

# 全局数据
video_data = {
    'video_path': '',
    'subtitles': [],
    'segments_to_remove': [],
    'confirmed': False,
    'confirmed_segments': []
}


@app.route('/')
def index():
    """审核界面"""
    html = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>视频审核</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { margin-bottom: 20px; }
        .controls { margin: 20px 0; }
        button { padding: 10px 20px; margin-right: 10px; font-size: 14px; cursor: pointer; }
        .timeline { border: 1px solid #ccc; padding: 10px; max-height: 400px; overflow-y: scroll; }
        .segment { padding: 8px; margin: 5px 0; border-radius: 4px; cursor: pointer; }
        .segment.selected { background-color: #ffcccc; }
        .segment.unselected { background-color: #fff; }
        .segment:hover { background-color: #f0f0f0; }
        .time { font-weight: bold; color: #333; }
        .reason { color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>AI视频审核</h1>
        <p>Shift + 点击片段可选中/取消。审核完成后点击"确认并剪辑"</p>
    </div>
    
    <div class="controls">
        <button onclick="selectAll()">全选</button>
        <button onclick="deselectAll()">全不选</button>
        <button onclick="confirm()">确认并剪辑</button>
    </div>
    
    <div class="timeline" id="timeline"></div>
    
    <script>
        let segments = {{ segments | tojson }};
        let selected = new Set(segments.map((_, i) => i));
        
        function render() {
            const timeline = document.getElementById('timeline');
            timeline.innerHTML = '';
            
            segments.forEach((seg, index) => {
                const div = document.createElement('div');
                div.className = 'segment ' + (selected.has(index) ? 'selected' : 'unselected');
                div.innerHTML = `
                    <span class="time">${seg.start.toFixed(2)}s - ${seg.end.toFixed(2)}s</span>
                    <span class="reason"> [${seg.reason}]</span>
                `;
                div.onclick = (e) => {
                    if (e.shiftKey) {
                        if (selected.has(index)) {
                            selected.delete(index);
                        } else {
                            selected.add(index);
                        }
                        render();
                    }
                };
                timeline.appendChild(div);
            });
        }
        
        function selectAll() {
            selected = new Set(segments.map((_, i) => i));
            render();
        }
        
        function deselectAll() {
            selected = new Set();
            render();
        }
        
        function confirm() {
            const confirmed = Array.from(selected).map(i => segments[i]);
            fetch('/confirm', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({segments: confirmed})
            }).then(r => r.json()).then(data => {
                alert('✅ ' + data.message);
            });
        }
        
        render();
    </script>
</body>
</html>
    '''
    return render_template_string(html, segments=video_data['segments_to_remove'])


@app.route('/confirm', methods=['POST'])
def confirm():
    """用户确认删除片段"""
    data = request.json
    video_data['confirmed_segments'] = data['segments']
    video_data['confirmed'] = True
    return jsonify({'status': 'ok', 'message': '审核完成！开始剪辑...'})


def start_server(video_path, subtitles, segments, port=5678):
    """启动审核服务器"""
    video_data['video_path'] = video_path
    video_data['subtitles'] = subtitles
    video_data['segments_to_remove'] = segments
    video_data['confirmed'] = False
    
    def run():
        app.run(host='0.0.0.0', port=port, debug=False)
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def wait_for_confirmation():
    """等待用户确认"""
    print("⏳ 等待审核...")
    while not video_data['confirmed']:
        import time
        time.sleep(0.5)
    return video_data['confirmed_segments']
