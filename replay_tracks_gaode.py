#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高德地图轨迹回放工具
读取 history_tracks.json 文件，在高德地图上按顺序回放轨迹点
"""

import json
import os
import webbrowser
from datetime import datetime
from pathlib import Path
import math

# 尝试导入查询模块，如果失败则提示
try:
    import query_tracks
    HAS_QUERY_MODULE = True
except ImportError:
    HAS_QUERY_MODULE = False


def parse_timestamp_to_datetime(timestamp_str):
    """
    将时间戳字符串转换为datetime对象
    
    Args:
        timestamp_str: 时间戳字符串，格式如 "2026-02-24 18:24:21"
    
    Returns:
        datetime对象
    """
    try:
        return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None


def wgs84_to_gcj02(lng, lat):
    """
    将WGS84坐标系（GPS坐标）转换为GCJ02坐标系（高德地图坐标）
    
    Args:
        lng: 经度（WGS84）
        lat: 纬度（WGS84）
    
    Returns:
        tuple: (经度（GCJ02）, 纬度（GCJ02）)
    """
    a = 6378245.0  # 长半轴
    ee = 0.00669342162296594323  # 偏心率平方
    
    def transform_lat(x, y):
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
        return ret
    
    def transform_lng(x, y):
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
        return ret
    
    d_lat = transform_lat(lng - 105.0, lat - 35.0)
    d_lng = transform_lng(lng - 105.0, lat - 35.0)
    rad_lat = lat / 180.0 * math.pi
    magic = math.sin(rad_lat)
    magic = 1 - ee * magic * magic
    sqrt_magic = math.sqrt(magic)
    d_lat = (d_lat * 180.0) / ((a * (1 - ee)) / (magic * sqrt_magic) * math.pi)
    d_lng = (d_lng * 180.0) / (a / sqrt_magic * math.cos(rad_lat) * math.pi)
    mg_lat = lat + d_lat
    mg_lng = lng + d_lng
    return mg_lng, mg_lat


def load_track_points(json_file):
    """
    从JSON文件加载轨迹点数据
    
    Args:
        json_file: JSON文件路径
    
    Returns:
        tuple: (设备信息, 查询信息, 轨迹点列表)
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    device_info = data.get('device_info', {})
    query_info = data.get('query_info', {})
    track_points = data.get('track_points', [])
    
    # 按时间戳排序
    track_points.sort(key=lambda x: parse_timestamp_to_datetime(x.get('timestamp', '')) or datetime.min)
    
    return device_info, query_info, track_points


def generate_html(device_info, query_info, track_points, output_file='track_replay_gaode.html', json_file_path='history_tracks.json'):
    """
    生成高德地图轨迹回放HTML文件
    
    Args:
        device_info: 设备信息（用于初始显示）
        query_info: 查询信息（用于初始显示）
        track_points: 轨迹点列表（用于初始显示和计算中心点）
        output_file: 输出HTML文件名
        json_file_path: JSON文件路径（HTML将动态加载此文件）
    """
    
    # 准备轨迹点数据（用于计算中心点和初始显示）
    points_js = []
    timestamps_ms = []  # 存储时间戳（毫秒）
    
    for i, point in enumerate(track_points):
        lat = point.get('latitude', 0)
        lng = point.get('longitude', 0)
        timestamp = point.get('timestamp', '')
        accuracy = point.get('accuracy', 'N/A')
        battery = point.get('batteryLevel', 'N/A')
        
        # 将GPS坐标（WGS84）转换为高德地图坐标（GCJ02）
        if lat != 0 and lng != 0:
            lng, lat = wgs84_to_gcj02(lng, lat)
        
        # 将时间戳字符串转换为时间戳（毫秒）
        timestamp_ms = 0
        if timestamp:
            try:
                dt = parse_timestamp_to_datetime(timestamp)
                if dt:
                    timestamp_ms = int(dt.timestamp() * 1000)
            except:
                pass
        
        timestamps_ms.append(timestamp_ms)
        
        points_js.append({
            'lat': lat,
            'lng': lng,
            'timestamp': timestamp,
            'timestampMs': timestamp_ms,  # 添加时间戳（毫秒）
            'accuracy': accuracy,
            'battery': battery,
            'index': i + 1
        })
    
    # 计算中心点和边界（使用转换后的坐标）
    if points_js:
        lats = [p['lat'] for p in points_js]
        lngs = [p['lng'] for p in points_js]
        center_lat = sum(lats) / len(lats)
        center_lng = sum(lngs) / len(lngs)
    else:
        center_lat = 26.09739
        center_lng = 119.3055
    
    device_name = device_info.get('name', '未知设备')
    device_sn = device_info.get('sn', 'N/A')
    total_points = len(track_points)
    
    # 生成JavaScript数据文件名（与HTML文件同目录）
    output_dir = os.path.dirname(os.path.abspath(output_file)) if os.path.dirname(output_file) else os.getcwd()
    js_data_file = os.path.splitext(output_file)[0] + '_data.js'
    js_data_file_name = os.path.basename(js_data_file)
    js_file_path = os.path.join(output_dir, js_data_file_name)
    
    # 读取JSON文件内容并转换为JavaScript变量
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # 生成JavaScript文件内容
        js_content = f"// 轨迹数据文件（自动生成）\n"
        js_content += f"// 从 {os.path.basename(json_file_path)} 生成\n"
        js_content += f"const trackData = {json.dumps(json_data, ensure_ascii=False, indent=2)};\n"
        
        # 写入JavaScript文件
        with open(js_file_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        print(f"✅ 已生成数据文件: {os.path.abspath(js_file_path)}")
    except Exception as e:
        print(f"⚠️  生成数据文件失败: {e}")
        js_data_file_name = None
    
    # 生成HTML内容
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>轨迹回放 - {device_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
        }}
        
        .header h1 {{
            font-size: 20px;
            margin-bottom: 5px;
        }}
        
        .header-info {{
            font-size: 12px;
            opacity: 0.9;
        }}
        
        .controls {{
            background: white;
            padding: 15px 20px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        
        .control-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        button {{
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            font-weight: 500;
        }}
        
        .btn-primary {{
            background: #667eea;
            color: white;
        }}
        
        .btn-primary:hover {{
            background: #5568d3;
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
        }}
        
        .btn-secondary {{
            background: #f0f0f0;
            color: #333;
        }}
        
        .btn-secondary:hover {{
            background: #e0e0e0;
        }}
        
        .btn-danger {{
            background: #ff6b6b;
            color: white;
        }}
        
        .btn-danger:hover {{
            background: #ee5a5a;
        }}
        
        .speed-control {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .speed-control label {{
            font-size: 14px;
            color: #666;
        }}
        
        .speed-control select {{
            padding: 6px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        
        .status {{
            margin-left: auto;
            padding: 8px 16px;
            background: #f8f9fa;
            border-radius: 6px;
            font-size: 14px;
            color: #495057;
        }}
        
        .status.active {{
            background: #d4edda;
            color: #155724;
        }}
        
        #mapContainer {{
            flex: 1;
            width: 100%;
            position: relative;
        }}
        
        .info-panel {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            min-width: 200px;
            z-index: 1000;
            font-size: 13px;
            cursor: default;
            user-select: none;
        }}
        
        .info-panel h3 {{
            margin-bottom: 10px;
            color: #333;
            font-size: 14px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 5px;
            cursor: move;
            user-select: none;
        }}
        
        .info-panel h3:hover {{
            background: rgba(102, 126, 234, 0.05);
            border-radius: 4px;
            padding: 5px;
            margin: -5px -5px 5px -5px;
        }}
        
        .info-item {{
            margin: 8px 0;
            display: flex;
            justify-content: space-between;
        }}
        
        .info-label {{
            color: #666;
            font-weight: 500;
        }}
        
        .info-value {{
            color: #333;
            font-weight: 600;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 4px;
            background: #e0e0e0;
            border-radius: 2px;
            margin-top: 10px;
            overflow: hidden;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s;
            width: 0%;
        }}
        
        .timeline-container {{
            background: white;
            padding: 15px 20px;
            border-bottom: 1px solid #e0e0e0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        
        .timeline-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .timeline-label {{
            font-size: 14px;
            font-weight: 500;
            color: #333;
        }}
        
        .timeline-date {{
            font-size: 13px;
            color: #667eea;
            font-weight: 600;
        }}
        
        .timeline-slider-container {{
            position: relative;
            width: 100%;
            height: 40px;
        }}
        
        .timeline-slider {{
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: #e0e0e0;
            outline: none;
            -webkit-appearance: none;
            appearance: none;
            cursor: pointer;
        }}
        
        .timeline-slider::-webkit-slider-thumb {{
            -webkit-appearance: none;
            appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #667eea;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(102, 126, 234, 0.4);
            transition: all 0.2s;
        }}
        
        .timeline-slider::-webkit-slider-thumb:hover {{
            background: #5568d3;
            transform: scale(1.1);
        }}
        
        .timeline-slider::-moz-range-thumb {{
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #667eea;
            cursor: pointer;
            border: none;
            box-shadow: 0 2px 6px rgba(102, 126, 234, 0.4);
            transition: all 0.2s;
        }}
        
        .timeline-slider::-moz-range-thumb:hover {{
            background: #5568d3;
            transform: scale(1.1);
        }}
        
        .timeline-marks {{
            display: flex;
            justify-content: space-between;
            margin-top: 5px;
            font-size: 11px;
            color: #999;
        }}
        
        .timeline-mark {{
            flex: 1;
            text-align: center;
        }}
    </style>
    <!-- 高德地图API - 需要申请API Key -->
    <!-- 申请地址: https://console.amap.com/dev/key/app -->
    <!-- 如果使用测试Key，地图上会显示水印 -->
    <script src="https://webapi.amap.com/maps?v=2.0&key=be36223b9dab65bb6b1f4bd5f9bb9442"></script>
    <script src="https://webapi.amap.com/ui/1.1/main.js"></script>
    {'<script src="' + js_data_file_name + '"></script>' if js_data_file_name else ''}
</head>
<body>
    <div class="header">
        <h1>📍 轨迹回放</h1>
        <div class="header-info">
            设备: {device_name} (SN: {device_sn}) | 总点数: {total_points}
        </div>
    </div>
    
    <div class="controls">
        <div class="control-group">
            <button class="btn-primary" onclick="startReplay()">▶ 开始回放</button>
            <button class="btn-secondary" onclick="pauseReplay()">⏸ 暂停</button>
            <button class="btn-secondary" onclick="stopReplay()">⏹ 停止</button>
            <button class="btn-secondary" onclick="resetReplay()">↺ 重置</button>
            <button class="btn-secondary" onclick="reloadData()" title="重新加载数据文件">🔄 刷新数据</button>
        </div>
        
        <div class="speed-control">
            <label>回放速度:</label>
            <select id="speedSelect" onchange="changeSpeed()">
                <option value="0.5">0.5x</option>
                <option value="1" selected>1x</option>
                <option value="2">2x</option>
                <option value="5">5x</option>
                <option value="10">10x</option>
            </select>
        </div>
        
        <div class="status" id="status">准备就绪</div>
    </div>
    
    <div class="timeline-container">
        <div class="timeline-header">
            <span class="timeline-label">📅 时间轴</span>
            <span class="timeline-date" id="timelineDate">-</span>
        </div>
        <div class="timeline-slider-container">
            <input type="range" id="timelineSlider" class="timeline-slider" min="0" max="100" value="0" step="1">
            <div class="timeline-marks" id="timelineMarks"></div>
        </div>
    </div>
    
    <div id="mapContainer"></div>
    
    <div class="info-panel">
        <h3>当前位置信息</h3>
        <div class="info-item">
            <span class="info-label">序号:</span>
            <span class="info-value" id="currentIndex">-</span>
        </div>
        <div class="info-item">
            <span class="info-label">时间:</span>
            <span class="info-value" id="currentTime">-</span>
        </div>
        <div class="info-item">
            <span class="info-label">纬度:</span>
            <span class="info-value" id="currentLat">-</span>
        </div>
        <div class="info-item">
            <span class="info-label">经度:</span>
            <span class="info-value" id="currentLng">-</span>
        </div>
        <div class="info-item">
            <span class="info-label">精度:</span>
            <span class="info-value" id="currentAccuracy">-</span>
        </div>
        <div class="info-item">
            <span class="info-label">电量:</span>
            <span class="info-value" id="currentBattery">-</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" id="progressFill"></div>
        </div>
    </div>

    <script>
        // 轨迹点数据（将从JavaScript数据文件加载）
        let trackPoints = [];
        
        // 地图相关变量
        let map;
        let polyline;
        let marker;
        let currentIndex = 0;
        let isPlaying = false;
        let replayTimer = null;
        let replaySpeed = 1; // 回放速度倍数
        
        // 时间轴相关变量
        let minTimestamp = 0;
        let maxTimestamp = 0;
        let timelineSlider = null;
        let isTimelineDragging = false;
        
        // 坐标转换函数（WGS84转GCJ02）
        function wgs84ToGcj02(lng, lat) {{
            const a = 6378245.0;
            const ee = 0.00669342162296594323;
            
            function transformLat(x, y) {{
                let ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
                ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0;
                ret += (20.0 * Math.sin(y * Math.PI) + 40.0 * Math.sin(y / 3.0 * Math.PI)) * 2.0 / 3.0;
                ret += (160.0 * Math.sin(y / 12.0 * Math.PI) + 320 * Math.sin(y * Math.PI / 30.0)) * 2.0 / 3.0;
                return ret;
            }}
            
            function transformLng(x, y) {{
                let ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
                ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0;
                ret += (20.0 * Math.sin(x * Math.PI) + 40.0 * Math.sin(x / 3.0 * Math.PI)) * 2.0 / 3.0;
                ret += (150.0 * Math.sin(x / 12.0 * Math.PI) + 300.0 * Math.sin(x / 30.0 * Math.PI)) * 2.0 / 3.0;
                return ret;
            }}
            
            let dLat = transformLat(lng - 105.0, lat - 35.0);
            let dLng = transformLng(lng - 105.0, lat - 35.0);
            let radLat = lat / 180.0 * Math.PI;
            let magic = Math.sin(radLat);
            magic = 1 - ee * magic * magic;
            let sqrtMagic = Math.sqrt(magic);
            dLat = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrtMagic) * Math.PI);
            dLng = (dLng * 180.0) / (a / sqrtMagic * Math.cos(radLat) * Math.PI);
            return [lng + dLng, lat + dLat];
        }}
        
        // 解析时间戳字符串为毫秒时间戳
        function parseTimestampToMs(timestampStr) {{
            if (!timestampStr) return 0;
            try {{
                // 格式：YYYY-MM-DD HH:MM:SS
                const parts = timestampStr.split(' ');
                if (parts.length === 2) {{
                    const datePart = parts[0].split('-');
                    const timePart = parts[1].split(':');
                    const dt = new Date(
                        parseInt(datePart[0]),
                        parseInt(datePart[1]) - 1,
                        parseInt(datePart[2]),
                        parseInt(timePart[0]),
                        parseInt(timePart[1]),
                        parseInt(timePart[2])
                    );
                    return dt.getTime();
                }}
            }} catch (e) {{
                console.error('解析时间戳失败:', timestampStr, e);
            }}
            return 0;
        }}
        
        // 数据文件路径
        const DATA_FILE_NAME = '{js_data_file_name if js_data_file_name else ""}';
        
        // 加载轨迹数据（从JavaScript数据文件）
        function loadTrackData() {{
            try {{
                document.getElementById('status').textContent = '正在加载数据...';
                
                // 检查全局变量 trackData 是否存在
                if (typeof trackData === 'undefined') {{
                    throw new Error('数据文件未加载，请确保数据文件存在');
                }}
                
                const data = trackData;
                
                // 处理轨迹点数据
                const rawPoints = data.track_points || [];
                trackPoints = [];
                
                for (let i = 0; i < rawPoints.length; i++) {{
                    const point = rawPoints[i];
                    let lat = point.latitude || 0;
                    let lng = point.longitude || 0;
                    const timestamp = point.timestamp || '';
                    const accuracy = point.accuracy || 'N/A';
                    const battery = point.batteryLevel || 'N/A';
                    
                    // 坐标转换
                    if (lat !== 0 && lng !== 0) {{
                        [lng, lat] = wgs84ToGcj02(lng, lat);
                    }}
                    
                    // 时间戳转换
                    const timestampMs = parseTimestampToMs(timestamp);
                    
                    trackPoints.push({{
                        lat: lat,
                        lng: lng,
                        timestamp: timestamp,
                        timestampMs: timestampMs,
                        accuracy: accuracy,
                        battery: battery,
                        index: i + 1
                    }});
                }}
                
                // 动态更新设备信息显示（根据实际加载的数据）
                const deviceInfo = data.device_info || {{}};
                const deviceName = deviceInfo.name || '未知设备';
                const deviceSn = deviceInfo.sn || 'N/A';
                const totalPoints = trackPoints.length;  // 使用实际加载的点数
                
                document.querySelector('.header h1').textContent = '📍 轨迹回放';
                document.querySelector('.header-info').textContent = 
                    `设备: ${{deviceName}} (SN: ${{deviceSn}}) | 总点数: ${{totalPoints}}`;
                
                // 如果地图已初始化，重新绘制轨迹（会自动重新计算中心点）
                if (map) {{
                    // 停止当前回放
                    stopReplay();
                    resetReplay();
                    
                    // 重新绘制轨迹（会根据新数据计算中心点）
                    drawTrack();
                    
                    // 重新初始化时间轴
                    initTimeline();
                }}
                
                document.getElementById('status').textContent = `数据加载完成（共 ${{totalPoints}} 个轨迹点）`;
                
                return true;
            }} catch (error) {{
                console.error('加载数据失败:', error);
                document.getElementById('status').textContent = '加载数据失败: ' + error.message;
                document.getElementById('status').classList.add('active');
                return false;
            }}
        }}
        
        // 重新加载数据文件
        function reloadData() {{
            if (!DATA_FILE_NAME) {{
                alert('数据文件路径未设置');
                return;
            }}
            
            // 停止当前回放
            stopReplay();
            
            // 移除旧的 script 标签
            const oldScript = document.querySelector(`script[src="${{DATA_FILE_NAME}}"]`);
            if (oldScript) {{
                oldScript.remove();
            }}
            
            // 清除旧的全局变量
            if (typeof trackData !== 'undefined') {{
                delete window.trackData;
            }}
            
            // 创建新的 script 标签（带时间戳避免缓存）
            const newScript = document.createElement('script');
            newScript.src = DATA_FILE_NAME + '?t=' + new Date().getTime();
            newScript.onload = function() {{
                // 数据文件加载完成后，处理数据
                loadTrackData();
            }};
            newScript.onerror = function() {{
                document.getElementById('status').textContent = '重新加载数据文件失败';
                document.getElementById('status').classList.add('active');
            }};
            
            document.head.appendChild(newScript);
        }}
        
        // 初始化时间轴
        function initTimeline() {{
            if (trackPoints.length === 0) return;
            
            // 找到最小和最大时间戳
            const timestamps = trackPoints.map(p => p.timestampMs).filter(ts => ts > 0);
            if (timestamps.length === 0) return;
            
            minTimestamp = Math.min(...timestamps);
            maxTimestamp = Math.max(...timestamps);
            
            // 设置滑块范围
            timelineSlider = document.getElementById('timelineSlider');
            timelineSlider.max = trackPoints.length - 1;
            timelineSlider.value = 0;
            
            // 更新时间轴标记
            updateTimelineMarks();
            
            // 添加滑块事件监听
            timelineSlider.addEventListener('input', function() {{
                isTimelineDragging = true;
                const index = parseInt(this.value);
                jumpToPoint(index);
            }});
            
            timelineSlider.addEventListener('mousedown', function() {{
                isTimelineDragging = true;
            }});
            
            timelineSlider.addEventListener('mouseup', function() {{
                isTimelineDragging = false;
            }});
        }}
        
        // 更新时间轴标记
        function updateTimelineMarks() {{
            const marksContainer = document.getElementById('timelineMarks');
            marksContainer.innerHTML = '';
            
            if (trackPoints.length === 0) return;
            
            // 显示5个标记点（开始、1/4、1/2、3/4、结束）
            const markPositions = [0, Math.floor(trackPoints.length / 4), Math.floor(trackPoints.length / 2), 
                                   Math.floor(trackPoints.length * 3 / 4), trackPoints.length - 1];
            
            markPositions.forEach((pos, idx) => {{
                if (pos >= trackPoints.length) return;
                const point = trackPoints[pos];
                const mark = document.createElement('div');
                mark.className = 'timeline-mark';
                
                if (point.timestamp) {{
                    // 只显示日期
                    const dateStr = point.timestamp.split(' ')[0];
                    mark.textContent = dateStr;
                }} else {{
                    mark.textContent = '';
                }}
                
                marksContainer.appendChild(mark);
            }});
        }}
        
        // 绘制轨迹线（根据实际数据动态计算中心点）
        function drawTrack() {{
            if (!map || trackPoints.length === 0) {{
                console.warn('无法绘制轨迹：地图未初始化或没有轨迹点数据');
                return;
            }}
            
            // 移除旧的轨迹线
            if (polyline) {{
                map.remove(polyline);
                polyline = null;
            }}
            
            // 绘制新的轨迹线
            const path = trackPoints.map(p => [p.lng, p.lat]);
            polyline = new AMap.Polyline({{
                path: path,
                isOutline: true,
                outlineColor: '#ffeeff',
                borderWeight: 3,
                strokeColor: '#3366FF',
                strokeOpacity: 0.6,
                strokeWeight: 3,
                lineJoin: 'round',
                lineCap: 'round',
                zIndex: 50
            }});
            map.add(polyline);
            
            // 根据实际数据动态计算中心点
            const lats = trackPoints.map(p => p.lat).filter(lat => lat !== 0);
            const lngs = trackPoints.map(p => p.lng).filter(lng => lng !== 0);
            
            if (lats.length > 0 && lngs.length > 0) {{
                // 计算中心点（平均值）
                const centerLat = lats.reduce((a, b) => a + b, 0) / lats.length;
                const centerLng = lngs.reduce((a, b) => a + b, 0) / lngs.length;
                
                // 更新地图中心点
                map.setCenter([centerLng, centerLat]);
                
                // 自适应显示（确保所有轨迹点都在视野内）
                map.setFitView([polyline], false, [50, 50, 50, 50]);
            }}
        }}
        
        // 跳转到指定数据点
        function jumpToPoint(index) {{
            if (index < 0 || index >= trackPoints.length) return;
            
            currentIndex = index;
            const point = trackPoints[index];
            
            // 更新标记点位置
            updateMarker(point);
            
            // 更新进度条
            const progress = ((index + 1) / trackPoints.length) * 100;
            document.getElementById('progressFill').style.width = progress + '%';
            
            // 更新时间轴滑块位置（不触发事件）
            if (timelineSlider) {{
                timelineSlider.value = index;
            }}
            
            // 更新时间轴日期显示
            if (point.timestamp) {{
                document.getElementById('timelineDate').textContent = point.timestamp;
            }}
        }}
        
        // 初始化地图（使用默认中心点，加载数据后会动态调整）
        function initMap() {{
            map = new AMap.Map('mapContainer', {{
                zoom: 15,
                center: [119.3055, 26.09739],  // 默认中心点（福州），加载数据后会动态调整
                mapStyle: 'amap://styles/normal'
            }});
            
            // 等待地图加载完成
            map.on('complete', function() {{
                // 异步加载控件插件
                AMap.plugin(['AMap.Scale', 'AMap.ToolBar'], function() {{
                    // 添加比例尺控件
                    var scale = new AMap.Scale();
                    map.addControl(scale);
                    
                    // 添加工具条控件
                    var toolbar = new AMap.ToolBar();
                    map.addControl(toolbar);
                }});
                
                // 创建标记点
                marker = new AMap.Marker({{
                    icon: new AMap.Icon({{
                        size: new AMap.Size(32, 32),
                        image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png',
                        imageOffset: new AMap.Pixel(-9, -3),
                        imageSize: new AMap.Size(18, 18)
                    }}),
                    offset: new AMap.Pixel(-9, -3),
                    zIndex: 100
                }});
                map.add(marker);
                
                // 加载轨迹数据（数据文件通过script标签已加载，这里直接处理）
                const loaded = loadTrackData();
                if (loaded && trackPoints.length > 0) {{
                    // 数据加载成功后，绘制轨迹
                    drawTrack();
                    // 初始化时间轴
                    initTimeline();
                    document.getElementById('status').textContent = '准备就绪';
                }} else {{
                    document.getElementById('status').textContent = '数据加载失败，请检查数据文件';
                    document.getElementById('status').classList.add('active');
                }}
            }});
        }}
        
        // 开始回放
        function startReplay() {{
            if (isPlaying) return;
            
            // 确保地图已初始化
            if (!map) {{
                console.error('地图未初始化，请等待地图加载完成');
                document.getElementById('status').textContent = '地图未就绪';
                return;
            }}
            
            if (currentIndex >= trackPoints.length) {{
                resetReplay();
            }}
            
            isPlaying = true;
            document.getElementById('status').textContent = '回放中...';
            document.getElementById('status').classList.add('active');
            
            replayTimer = setInterval(() => {{
                if (currentIndex >= trackPoints.length) {{
                    stopReplay();
                    return;
                }}
                
                const point = trackPoints[currentIndex];
                updateMarker(point);
                
                // 更新时间轴滑块位置（不触发input事件）
                if (timelineSlider && !isTimelineDragging) {{
                    timelineSlider.value = currentIndex;
                }}
                
                // 更新时间轴日期显示
                if (point.timestamp) {{
                    document.getElementById('timelineDate').textContent = point.timestamp;
                }}
                
                currentIndex++;
                
                // 更新进度
                const progress = (currentIndex / trackPoints.length) * 100;
                document.getElementById('progressFill').style.width = progress + '%';
            }}, 1000 / replaySpeed); // 根据速度调整间隔
        }}
        
        // 暂停回放
        function pauseReplay() {{
            if (!isPlaying) return;
            
            isPlaying = false;
            clearInterval(replayTimer);
            document.getElementById('status').textContent = '已暂停';
            document.getElementById('status').classList.remove('active');
        }}
        
        // 停止回放
        function stopReplay() {{
            isPlaying = false;
            clearInterval(replayTimer);
            document.getElementById('status').textContent = '已停止';
            document.getElementById('status').classList.remove('active');
        }}
        
        // 重置回放
        function resetReplay() {{
            stopReplay();
            currentIndex = 0;
            document.getElementById('progressFill').style.width = '0%';
            updateInfoPanel(null);
            document.getElementById('status').textContent = '准备就绪';
            
            // 重置时间轴
            if (timelineSlider) {{
                timelineSlider.value = 0;
            }}
            document.getElementById('timelineDate').textContent = '-';
        }}
        
        // 改变回放速度
        function changeSpeed() {{
            replaySpeed = parseFloat(document.getElementById('speedSelect').value);
            if (isPlaying) {{
                pauseReplay();
                startReplay();
            }}
        }}
        
        // 更新标记点位置
        function updateMarker(point) {{
            if (!map) {{
                console.error('地图未初始化');
                return;
            }}
            if (!marker) {{
                // 如果标记点不存在，先创建它
                marker = new AMap.Marker({{
                    icon: new AMap.Icon({{
                        size: new AMap.Size(32, 32),
                        image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png',
                        imageOffset: new AMap.Pixel(-9, -3),
                        imageSize: new AMap.Size(18, 18)
                    }}),
                    offset: new AMap.Pixel(-9, -3),
                    zIndex: 100
                }});
                map.add(marker);
            }}
            marker.setPosition([point.lng, point.lat]);
            // 不移动地图中心，只更新标记点位置
            updateInfoPanel(point);
        }}
        
        // 更新信息面板
        function updateInfoPanel(point) {{
            if (!point) {{
                document.getElementById('currentIndex').textContent = '-';
                document.getElementById('currentTime').textContent = '-';
                document.getElementById('currentLat').textContent = '-';
                document.getElementById('currentLng').textContent = '-';
                document.getElementById('currentAccuracy').textContent = '-';
                document.getElementById('currentBattery').textContent = '-';
                return;
            }}
            
            document.getElementById('currentIndex').textContent = point.index + ' / ' + trackPoints.length;
            document.getElementById('currentTime').textContent = point.timestamp;
            document.getElementById('currentLat').textContent = point.lat.toFixed(6);
            document.getElementById('currentLng').textContent = point.lng.toFixed(6);
            document.getElementById('currentAccuracy').textContent = point.accuracy + 'm';
            document.getElementById('currentBattery').textContent = point.battery + '%';
        }}
        
        // 初始化信息面板拖拽功能
        function initInfoPanelDrag() {{
            const infoPanel = document.querySelector('.info-panel');
            const header = infoPanel.querySelector('h3');
            let isDragging = false;
            let currentX;
            let currentY;
            let initialX;
            let initialY;
            let xOffset = 0;
            let yOffset = 0;
            
            // 从localStorage恢复位置
            const savedPosition = localStorage.getItem('infoPanelPosition');
            if (savedPosition) {{
                const pos = JSON.parse(savedPosition);
                infoPanel.style.left = pos.left;
                infoPanel.style.right = 'auto';
                infoPanel.style.top = pos.top;
                infoPanel.style.bottom = 'auto';
                xOffset = pos.xOffset || 0;
                yOffset = pos.yOffset || 0;
            }}
            
            header.addEventListener('mousedown', dragStart);
            document.addEventListener('mousemove', drag);
            document.addEventListener('mouseup', dragEnd);
            
            function dragStart(e) {{
                if (e.button !== 0) return; // 只响应左键
                
                initialX = e.clientX - xOffset;
                initialY = e.clientY - yOffset;
                
                if (e.target === header || header.contains(e.target)) {{
                    isDragging = true;
                    header.style.cursor = 'grabbing';
                }}
            }}
            
            function drag(e) {{
                if (isDragging) {{
                    e.preventDefault();
                    
                    currentX = e.clientX - initialX;
                    currentY = e.clientY - initialY;
                    
                    xOffset = currentX;
                    yOffset = currentY;
                    
                    // 获取面板尺寸和容器尺寸
                    const panelRect = infoPanel.getBoundingClientRect();
                    const container = document.getElementById('mapContainer');
                    const containerRect = container.getBoundingClientRect();
                    
                    // 计算边界限制
                    const minX = 0;
                    const minY = 0;
                    const maxX = containerRect.width - panelRect.width;
                    const maxY = containerRect.height - panelRect.height;
                    
                    // 限制在容器内
                    let newX = Math.max(minX, Math.min(maxX, currentX));
                    let newY = Math.max(minY, Math.min(maxY, currentY));
                    
                    // 使用left和top定位
                    infoPanel.style.left = newX + 'px';
                    infoPanel.style.right = 'auto';
                    infoPanel.style.top = newY + 'px';
                    infoPanel.style.bottom = 'auto';
                    
                    xOffset = newX;
                    yOffset = newY;
                }}
            }}
            
            function dragEnd(e) {{
                if (isDragging) {{
                    initialX = currentX;
                    initialY = currentY;
                    isDragging = false;
                    header.style.cursor = 'move';
                    
                    // 保存位置到localStorage
                    const rect = infoPanel.getBoundingClientRect();
                    const containerRect = document.getElementById('mapContainer').getBoundingClientRect();
                    const savedPos = {{
                        left: infoPanel.style.left,
                        top: infoPanel.style.top,
                        xOffset: xOffset,
                        yOffset: yOffset
                    }};
                    localStorage.setItem('infoPanelPosition', JSON.stringify(savedPos));
                }}
            }}
        }}
        
        // 页面加载完成后初始化
        window.onload = function() {{
            // 初始化信息面板拖拽功能
            initInfoPanelDrag();
            
            // 初始化地图（地图加载完成后会自动加载数据）
            initMap();
        }};
    </script>
</body>
</html>'''
    
    # 写入HTML文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_file


def main():
    """主函数"""
    print("=" * 60)
    print("高德地图轨迹回放工具")
    print("=" * 60)
    
    # 默认JSON文件路径
    json_file = "history_tracks.json"
    
    # 如果命令行提供了文件路径，使用命令行参数
    import sys
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    
    # 如果文件不存在，尝试自动生成
    if not os.path.exists(json_file):
        print(f"⚠️  文件不存在: {json_file}")
        
        if HAS_QUERY_MODULE:
            print(f"\n尝试自动生成文件...")
            choice = input(f"是否调用快捷查询功能生成 {json_file}? (y/n，默认y): ").strip().lower()
            
            if choice != 'n':
                print("\n" + "=" * 60)
                print("开始快捷查询...")
                print("=" * 60)
                
                try:
                    # 调用快捷查询功能
                    result = query_tracks.quick_query(
                        sn=None,  # 使用默认设备序列号
                        output_file=json_file,
                        max_pages=10
                    )
                    
                    if result:
                        print(f"\n✅ 文件已生成: {os.path.abspath(json_file)}")
                    else:
                        print(f"\n❌ 文件生成失败")
                        return
                except Exception as e:
                    print(f"\n❌ 生成文件时出错: {e}")
                    import traceback
                    traceback.print_exc()
                    return
            else:
                print(f"❌ 用户取消，退出")
                return
        else:
            print(f"❌ 错误: 找不到文件 {json_file}")
            print(f"   请确保文件存在，或提供正确的文件路径")
            print(f"\n提示: 如果 query_tracks.py 在同一目录下，可以自动生成文件")
            return
    else:
        # 文件存在，询问是否要更新
        if HAS_QUERY_MODULE:
            print(f"✅ 文件已存在: {json_file}")
            update_choice = input(f"是否重新查询更新文件? (y/n，默认n): ").strip().lower()
            
            if update_choice == 'y':
                print("\n" + "=" * 60)
                print("开始快捷查询更新文件...")
                print("=" * 60)
                
                try:
                    # 调用快捷查询功能更新文件
                    result = query_tracks.quick_query(
                        sn=None,  # 使用默认设备序列号
                        output_file=json_file,
                        max_pages=10
                    )
                    
                    if result:
                        print(f"\n✅ 文件已更新: {os.path.abspath(json_file)}")
                    else:
                        print(f"\n⚠️  文件更新失败，将使用现有文件")
                except Exception as e:
                    print(f"\n⚠️  更新文件时出错: {e}")
                    print(f"   将使用现有文件")
                    import traceback
                    traceback.print_exc()
    
    print(f"📂 读取文件: {json_file}")
    
    try:
        # 加载轨迹点数据
        device_info, query_info, track_points = load_track_points(json_file)
        
        print(f"✅ 成功加载 {len(track_points)} 个轨迹点")
        print(f"   设备: {device_info.get('name', 'N/A')} (SN: {device_info.get('sn', 'N/A')})")
        
        if len(track_points) == 0:
            print("⚠️  警告: 没有轨迹点数据")
            return
        
        # 生成HTML文件（传递JSON文件路径，HTML将动态加载）
        output_file = generate_html(device_info, query_info, track_points, 
                                   output_file='track_replay_gaode.html',
                                   json_file_path=json_file)
        abs_path = os.path.abspath(output_file)
        
        print(f"\n✅ HTML文件已生成: {abs_path}")
        print(f"\n⚠️  注意: 需要高德地图API Key才能正常显示地图")
        print(f"   请访问 https://console.amap.com/dev/key/app 申请API Key")
        print(f"   然后在生成的HTML文件中替换 YOUR_API_KEY")
        
        # 询问是否在浏览器中打开
        try:
            choice = input("\n是否在浏览器中打开? (y/n，默认y): ").strip().lower()
            if choice != 'n':
                webbrowser.open(f'file://{abs_path}')
                print("✅ 已在浏览器中打开")
        except:
            pass
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
