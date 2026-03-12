#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 CityTag API 请求体的工具
用于生成 /api/interface/v2/device3/{uid} 接口的请求体
"""

import json
import base64
import os
from datetime import datetime, timedelta
from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad

# 尝试导入 requests，如果未安装会提示
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Token 存储文件路径（存储在脚本同目录下）
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.citytag_token.json')


def des3_decode_ecb(key: str, ciphertext: str) -> str:
    """
    使用 3DES/ECB/PKCS5Padding 解密 Base64 编码的字符串
    
    Args:
        key: 解密密钥（用户的 token）
        ciphertext: Base64 编码的加密字符串
    
    Returns:
        解密后的明文（JSON 字符串）
    """
    # 将密钥转换为字节，确保密钥长度为 24 字节（3DES 需要）
    key_bytes = key.encode('utf-8')
    
    # 如果密钥长度不是 24 字节，需要处理
    if len(key_bytes) < 24:
        # 如果密钥长度小于 24，重复填充到 24 字节
        key_bytes = (key_bytes * ((24 // len(key_bytes)) + 1))[:24]
    elif len(key_bytes) > 24:
        # 如果密钥长度大于 24，截取前 24 字节
        key_bytes = key_bytes[:24]
    
    # Base64 解码
    encrypted_bytes = base64.b64decode(ciphertext)
    
    # 创建 3DES 解密器（ECB 模式）
    cipher = DES3.new(key_bytes, DES3.MODE_ECB)
    
    # 解密
    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    
    # 去除 PKCS5Padding（在 Python 中对应 PKCS7）
    from Crypto.Util.Padding import unpad
    plaintext_bytes = unpad(decrypted_bytes, DES3.block_size)
    
    # 转换为字符串
    plaintext = plaintext_bytes.decode('utf-8')
    
    return plaintext


def des3_encode_ecb(key: str, plaintext: str) -> str:
    """
    使用 3DES/ECB/PKCS5Padding 加密字符串，然后进行 Base64 编码
    
    Args:
        key: 加密密钥（用户的 token）
        plaintext: 要加密的明文（JSON 字符串）
    
    Returns:
        Base64 编码后的加密字符串
    """
    # 将密钥转换为字节，确保密钥长度为 24 字节（3DES 需要）
    key_bytes = key.encode('utf-8')
    
    # 如果密钥长度不是 24 字节，需要处理
    if len(key_bytes) < 24:
        # 如果密钥长度小于 24，重复填充到 24 字节
        key_bytes = (key_bytes * ((24 // len(key_bytes)) + 1))[:24]
    elif len(key_bytes) > 24:
        # 如果密钥长度大于 24，截取前 24 字节
        key_bytes = key_bytes[:24]
    
    # 将明文转换为字节
    plaintext_bytes = plaintext.encode('utf-8')
    
    # 使用 PKCS5Padding（在 Python 中对应 PKCS7）
    padded_plaintext = pad(plaintext_bytes, DES3.block_size)
    
    # 创建 3DES 加密器（ECB 模式）
    cipher = DES3.new(key_bytes, DES3.MODE_ECB)
    
    # 加密
    encrypted_bytes = cipher.encrypt(padded_plaintext)
    
    # Base64 编码
    encrypted_base64 = base64.b64encode(encrypted_bytes).decode('utf-8')
    
    return encrypted_base64


def generate_request_body(token: str, uid: int = None, sn: str = None, 
                         start_time: int = None, end_time: int = None,
                         start_time_str: str = None, end_time_str: str = None,
                         page_no: int = None, page_size: int = None) -> dict:
    """
    生成 API 请求体
    
    Args:
        token: 用户 token（用于加密）
        uid: 用户 ID
        sn: 设备序列号（查询设备轨迹时需要）
        start_time: 开始时间戳（毫秒，查询设备轨迹时需要）
                     例如：获取历史轨迹点时，需要指定时间范围
                     注意：如果同时提供了 start_time_str，优先使用 start_time_str
        end_time: 结束时间戳（毫秒，查询设备轨迹时需要）
                   例如：获取历史轨迹点时，需要指定时间范围
                   注意：如果同时提供了 end_time_str，优先使用 end_time_str
        start_time_str: 开始时间字符串（格式：YYYY-MM-DD HH:MM:SS）
                        例如："2026-03-01 16:52:49"
        end_time_str: 结束时间字符串（格式：YYYY-MM-DD HH:MM:SS）
                      例如："2026-03-04 16:52:49"
        page_no: 页码（分页查询时需要）
        page_size: 每页大小（分页查询时需要）
    
    Returns:
        包含 encryption 字段的请求体字典
    
    示例 - 获取历史轨迹点（使用字符串格式时间）:
        request_body = generate_request_body(
            token=token,
            uid=242487,
            sn="201607813254",
            start_time_str="2026-03-01 16:52:49",
            end_time_str="2026-03-04 16:52:49"
        )
        
    示例 - 获取历史轨迹点（使用时间戳）:
        from datetime import datetime
        
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = end_time - 24 * 60 * 60 * 1000
        
        request_body = generate_request_body(
            token=token,
            uid=242487,
            sn="201607813254",
            start_time=start_time,
            end_time=end_time
        )
        
        返回的数据结构中，每个设备对象包含 historyList 字段，
        里面是多个历史轨迹点（TrackData）的数组。
        每个轨迹点包含：latitude, longitude, timestamp, accuracy 等字段。
        
    参考: 获取历史轨迹点说明.md
    """
    # 构建业务数据
    business_data = {}
    
    if uid is not None:
        business_data['uid'] = uid
    
    # 判断是设备轨迹查询还是分页查询
    # 注意：根据API实际行为：
    # 1. 如果提供了 sn，使用 sn + 时间范围参数（startTime + endTime）查询指定设备
    # 2. 如果提供了 sn + 分页参数，使用 sn + 分页参数查询指定设备
    # 3. 如果只提供了分页参数，查询所有设备
    if sn is not None:
        # 设备查询场景（带sn）
        business_data['sn'] = sn
        
        # 处理时间范围参数（优先使用字符串格式）
        if start_time_str is not None and end_time_str is not None:
            # 使用字符串格式的时间
            business_data['startTime'] = start_time_str
            business_data['endTime'] = end_time_str
        elif start_time is not None and end_time is not None:
            # 将时间戳转换为字符串格式
            start_dt = datetime.fromtimestamp(start_time / 1000)
            end_dt = datetime.fromtimestamp(end_time / 1000)
            business_data['startTime'] = start_dt.strftime('%Y-%m-%d %H:%M:%S')
            business_data['endTime'] = end_dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 如果同时提供了分页参数，添加分页信息
        if page_no is not None and page_size is not None:
            business_data['pageNo'] = page_no
            business_data['pageSize'] = page_size
    elif page_no is not None and page_size is not None:
        # 纯分页查询场景（不带sn，查询所有设备）
        business_data['pageNo'] = page_no
        business_data['pageSize'] = page_size
    
    # 将业务数据转换为 JSON 字符串
    json_string = json.dumps(business_data, ensure_ascii=False, separators=(',', ':'))
    
    # 使用 3DES 加密并 Base64 编码
    encrypted_data = des3_encode_ecb(token, json_string)
    
    # 构建最终的请求体
    request_body = {
        "encryption": encrypted_data
    }
    
    return request_body


def call_and_decrypt_api(token: str, uid: int, request_body: dict = None,
                         sn: str = None, start_time: int = None, end_time: int = None,
                         start_time_str: str = None, end_time_str: str = None,
                         page_no: int = None, page_size: int = None) -> dict:
    """
    生成请求体、发送请求、解密响应并返回结果
    
    Args:
        token: 用户 token
        uid: 用户 ID
        request_body: 可选的请求体（如果提供，直接使用；否则根据其他参数生成）
        sn: 设备序列号（设备轨迹查询时需要）
        start_time: 开始时间戳（毫秒，设备轨迹查询时需要）
        end_time: 结束时间戳（毫秒，设备轨迹查询时需要）
        start_time_str: 开始时间字符串（格式：YYYY-MM-DD HH:MM:SS）
        end_time_str: 结束时间字符串（格式：YYYY-MM-DD HH:MM:SS）
        page_no: 页码（分页查询时需要）
        page_size: 每页大小（分页查询时需要）
    
    Returns:
        解密后的响应数据（字典），如果失败返回 None
    """
    if not HAS_REQUESTS:
        print("错误: 需要安装 requests 库才能发送请求")
        print("请运行: pip install requests")
        return None
    
    # 如果没有提供请求体，则生成
    if request_body is None:
        # 如果提供了 sn，使用 sn + 时间范围参数（字符串格式）或分页参数
        # 如果只提供了分页参数，使用纯分页查询
        request_body = generate_request_body(
            token=token,
            uid=uid,
            sn=sn,
            start_time=start_time,
            end_time=end_time,
            start_time_str=start_time_str,
            end_time_str=end_time_str,
            page_no=page_no,
            page_size=page_size
        )
    
    # 构建 URL
    url = f"https://citytag.yuminstall.top/api/interface/v2/device3/{uid}"
    
    # 设置请求头
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "CityTag"
    }
    
    print("\n" + "=" * 60)
    print("发送请求")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"请求体:")
    print(json.dumps(request_body, indent=2, ensure_ascii=False))
    
    try:
        # 发送请求
        response = requests.post(url, json=request_body, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 解析响应
        response_data = response.json()
        
        print("\n" + "=" * 60)
        print("响应信息")
        print("=" * 60)
        print(f"HTTP 状态码: {response.status_code}")
        print(f"响应码: {response_data.get('code')}")
        print(f"响应消息: {response_data.get('msg')}")
        
        # 检查响应码
        if response_data.get('code') != '00000':
            print(f"\n❌ 请求失败: {response_data.get('msg')}")
            return None
        
        # 获取加密的数据
        encrypted_data = response_data.get('data')
        if not encrypted_data:
            print("\n❌ 响应中没有 data 字段")
            return None
        
        print(f"\n加密的 data 字段长度: {len(encrypted_data)} 字符")
        print(f"加密数据预览: {encrypted_data[:80]}...")
        
        # 解密数据
        print("\n" + "=" * 60)
        print("开始解密...")
        print("=" * 60)
        
        try:
            decrypted_data = decrypt_api_response(token, encrypted_data)
            
            print("\n" + "=" * 60)
            print("✅ 解密成功！解密后的数据:")
            print("=" * 60)
            print(json.dumps(decrypted_data, indent=2, ensure_ascii=False))
            
            return decrypted_data
            
        except Exception as e:
            print(f"\n❌ 解密失败: {e}")
            import traceback
            traceback.print_exc()
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求错误: {e}")
        return None
    except Exception as e:
        print(f"\n❌ 处理错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def decrypt_api_response(token: str, encrypted_data: str) -> dict:
    """
    解密 API 响应数据
    
    Args:
        token: 用户 token（用于解密）
        encrypted_data: 加密的 Base64 字符串（来自响应的 data 字段）
    
    Returns:
        解密后的 JSON 对象（字典）
    """
    try:
        # 解密数据
        decrypted_json = des3_decode_ecb(token, encrypted_data)
        
        # 解析 JSON
        decrypted_data = json.loads(decrypted_json)
        
        return decrypted_data
    except Exception as e:
        raise Exception(f"解密失败: {e}")


def save_token_to_file(token: str, uid: int, username: str = None) -> bool:
    """
    将 token 和用户信息保存到文件
    
    Args:
        token: 用户 token
        uid: 用户 ID
        username: 用户名（可选）
    
    Returns:
        是否保存成功
    """
    try:
        token_data = {
            "token": token,
            "uid": uid,
            "username": username
        }
        
        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"保存 token 失败: {e}")
        return False


def load_token_from_file() -> tuple:
    """
    从文件读取 token 和用户信息
    
    Returns:
        (token, uid, username) 元组，如果文件不存在或读取失败返回 (None, None, None)
    """
    try:
        if not os.path.exists(TOKEN_FILE):
            return None, None, None
        
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            token_data = json.load(f)
        
        token = token_data.get('token')
        uid = token_data.get('uid')
        username = token_data.get('username')
        
        if token and uid:
            return token, uid, username
        else:
            return None, None, None
    except Exception as e:
        print(f"读取 token 失败: {e}")
        return None, None, None


def clear_token_file() -> bool:
    """
    清除保存的 token 文件
    
    Returns:
        是否清除成功
    """
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        return True
    except Exception as e:
        print(f"清除 token 文件失败: {e}")
        return False


# 默认配置
DEFAULT_USERNAME = "18659179970"
DEFAULT_PASSWORD = "awen5221"
DEFAULT_DEVICE_SN = "201607813254"  # 默认设备序列号
DEFAULT_QUERY_DAYS = 30  # 快捷查询默认查询天数


def login_and_get_token(username: str = None, password: str = None, save_token: bool = True) -> tuple:
    """
    通过登录接口获取 token
    
    Args:
        username: 用户名（如果不提供，使用默认值）
        password: 密码（如果不提供，使用默认值）
    
    Returns:
        (token, uid) 元组，如果登录失败返回 (None, None)
    
    注意: 需要先安装 requests 库: pip install requests
    """
    # 如果未提供，使用默认值
    if username is None:
        username = DEFAULT_USERNAME
    if password is None:
        password = DEFAULT_PASSWORD
    
    # 如果未提供，使用默认值
    if username is None:
        username = DEFAULT_USERNAME
    if password is None:
        password = DEFAULT_PASSWORD
    
    try:
        import requests
        
        login_url = "https://citytag.yuminstall.top/api/interface/login"
        login_params = {
            "username": username,
            "password": password
        }
        
        response = requests.post(login_url, params=login_params)
        result = response.json()
        
        if result.get("code") == "00000":
            data = result.get("data", {})
            token = data.get("token")
            uid = data.get("id")
            print(f"登录成功！")
            print(f"Token: {token}")
            print(f"用户ID: {uid}")
            
            # 保存 token 到文件
            if save_token:
                if save_token_to_file(token, uid, username):
                    print(f"✅ Token 已保存到: {TOKEN_FILE}")
                else:
                    print("⚠️  Token 保存失败，但登录成功")
            
            return token, uid
        else:
            print(f"登录失败: {result.get('msg', '未知错误')}")
            return None, None
    except ImportError:
        print("错误: 需要安装 requests 库才能使用登录功能")
        print("请运行: pip install requests")
        return None, None
    except Exception as e:
        print(f"登录出错: {e}")
        return None, None


def _print_track_point(point: dict, index: int):
    """打印单个轨迹点的信息"""
    print(f"\n点 {index}:")
    print(f"  纬度: {point.get('latitude')}")
    print(f"  经度: {point.get('longitude')}")
    print(f"  时间戳: {point.get('timestamp')}")
    if point.get('timestamp'):
        try:
            ts = parse_timestamp_to_ms(point.get('timestamp'))
            if ts > 0:
                dt = datetime.fromtimestamp(ts / 1000)
                print(f"  时间: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            pass
    print(f"  精度: {point.get('accuracy', 'N/A')}")
    print(f"  置信度: {point.get('confidence', 'N/A')}")
    if point.get('batteryLevel') is not None:
        print(f"  电量: {point.get('batteryLevel')}%")
    print(f"  更新时间: {point.get('updatetime', 'N/A')}")


def parse_timestamp_to_ms(timestamp_value) -> int:
    """
    将时间戳值转换为毫秒时间戳
    
    支持多种格式：
    1. 日期时间字符串：如 "2026-03-04 13:18:33"
    2. 毫秒时间戳（整数或字符串）：如 1709543913000
    3. 秒时间戳（整数或字符串）：如 1709543913
    
    Args:
        timestamp_value: 时间戳值（可能是字符串日期时间、整数时间戳等）
    
    Returns:
        毫秒时间戳（整数），解析失败返回0
    """
    if timestamp_value is None:
        return 0
    
    # 如果是字符串，先尝试解析为日期时间格式
    if isinstance(timestamp_value, str):
        # 尝试解析日期时间字符串格式：如 "2026-03-04 13:18:33" 或 "2026-03-04"
        try:
            # 尝试完整格式：YYYY-MM-DD HH:MM:SS
            if ' ' in timestamp_value and ':' in timestamp_value:
                dt = datetime.strptime(timestamp_value, "%Y-%m-%d %H:%M:%S")
            # 尝试日期格式：YYYY-MM-DD
            elif '-' in timestamp_value and len(timestamp_value) == 10:
                dt = datetime.strptime(timestamp_value, "%Y-%m-%d")
            else:
                # 如果不是日期格式，尝试作为数字字符串
                ts = int(timestamp_value)
                if ts < 1000000000000:
                    return ts * 1000
                return ts
            return int(dt.timestamp() * 1000)
        except (ValueError, TypeError):
            # 如果日期解析失败，尝试作为数字字符串
            try:
                ts = int(timestamp_value)
                if ts < 1000000000000:
                    return ts * 1000
                return ts
            except (ValueError, TypeError):
                return 0
    
    # 如果是数字，直接处理
    if isinstance(timestamp_value, (int, float)):
        ts = int(timestamp_value)
        if ts < 1000000000000:
            return ts * 1000
        return ts
    
    return 0


def get_timestamp_ms(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0) -> int:
    """
    将日期时间转换为毫秒时间戳
    
    Args:
        year, month, day, hour, minute, second: 日期时间
    
    Returns:
        毫秒时间戳
    """
    dt = datetime(year, month, day, hour, minute, second)
    return int(dt.timestamp() * 1000)


def quick_query(sn: str = None, output_file: str = "history_tracks.json", 
                     max_pages: int = 10) -> dict:
    """
    快捷查询：使用默认值查询指定天数内的历史轨迹点，去重后合并到JSON文件
    
    Args:
        sn: 设备序列号（如果不提供，使用默认值）
        output_file: 输出JSON文件名
        max_pages: 最大查询页数（防止无限查询）
    
    Returns:
        合并后的历史轨迹点数据
    """
    if sn is None:
        sn = DEFAULT_DEVICE_SN
    
    print("=" * 60)
    print(f"快捷查询：{DEFAULT_QUERY_DAYS}天内的历史轨迹点")
    print("=" * 60)
    print(f"设备序列号: {sn}")
    print(f"输出文件: {output_file}")
    
    # 获取token（优先从文件读取）
    token, uid = get_token_and_uid(force_login=False)
    if not token:
        print("❌ 无法获取 token，退出")
        return None
    
    # 计算默认天数前的时间（使用字符串格式，与解密出的参数格式一致）
    end_time = datetime.now() #  - timedelta(days=DEFAULT_QUERY_DAYS)
    start_time = end_time - timedelta(days=DEFAULT_QUERY_DAYS)
    
    # 格式化为字符串格式：YYYY-MM-DD HH:MM:SS
    start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
    end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"时间范围: {start_time_str} 到 {end_time_str}")
    print(f"时间跨度: {DEFAULT_QUERY_DAYS} 天")
    
    # 存储所有去重后的轨迹点
    all_track_points = []
    device_info = None
    
    # 分页查询，合并所有数据
    page_no = 1
    page_size = 100  # 使用较大的page_size
    
    print(f"\n开始分页查询（最多 {max_pages} 页）...")
    
    # 计算时间戳用于客户端筛选
    start_time_ms = int(start_time.timestamp() * 1000)
    end_time_ms = int(end_time.timestamp() * 1000)
    
    while page_no <= max_pages:
        print(f"\n查询第 {page_no} 页 (pageSize={page_size})...")
        
        # 查询当前页（使用字符串格式的时间范围参数）
        result = call_and_decrypt_api(
            token=token,
            uid=uid,
            sn=sn,
            start_time_str=start_time_str,  # 使用字符串格式的时间
            end_time_str=end_time_str,
            page_no=page_no,
            page_size=page_size
        )
        
        if not result:
            print(f"第 {page_no} 页查询失败或没有数据")
            if page_no == 1:
                print("\n⚠️  第一页查询失败，可能的原因:")
                print("1. Token 已过期，需要重新登录")
                print("2. 设备序列号不正确")
                print("3. API 返回错误")
                print("\n建议: 检查 token 和设备序列号是否正确")
            break
        
        # 解析结果
        if isinstance(result, list) and len(result) > 0:
            device = result[0]
            
            # 保存设备信息（只在第一页时保存）
            if device_info is None:
                device_info = {
                    'sn': device.get('sn'),
                    'name': device.get('name'),
                    'mac': device.get('mac'),
                    'cid': device.get('cid'),
                    'uid': device.get('uid'),
                    'status': device.get('status'),
                    'timestamp': device.get('timestamp'),
                    'updatetime': device.get('updatetime'),
                    'createtime': device.get('createtime'),
                }
            
            # 获取历史轨迹点
            history_list = device.get('historyList', [])
            
            if not history_list:
                print(f"第 {page_no} 页没有历史轨迹点（historyList 为空）")
                # 显示设备信息以便调试
                print(f"  设备信息: sn={device.get('sn')}, name={device.get('name')}")
                print(f"  设备最后更新时间: {device.get('updatetime', 'N/A')}")
                break
            
            print(f"  获取到 {len(history_list)} 个轨迹点")
            
            # 显示前几个轨迹点的时间戳（用于调试）
            if page_no == 1 and len(history_list) > 0:
                print(f"  前3个轨迹点的时间戳示例:")
                for i, point in enumerate(history_list[:3], 1):
                    ts_raw = point.get('timestamp')
                    if ts_raw:
                        ts_val = parse_timestamp_to_ms(ts_raw)
                        if ts_val > 0:
                            dt = datetime.fromtimestamp(ts_val / 1000)
                            print(f"    点{i}: {ts_raw} -> {dt.strftime('%Y-%m-%d %H:%M:%S')} (时间戳: {ts_val})")
                        else:
                            print(f"    点{i}: {ts_raw} (无法解析)")
                    else:
                        print(f"    点{i}: (无时间戳)")
            
            # 筛选时间范围内的轨迹点（使用时间戳进行筛选）
            filtered_points = []
            time_out_of_range_count = 0
            
            for point in history_list:
                point_timestamp = point.get('timestamp')
                if point_timestamp:
                    # 使用统一的解析函数处理时间戳
                    ts = parse_timestamp_to_ms(point_timestamp)
                    
                    if ts > 0:
                        # 使用时间戳进行筛选（start_time_ms 和 end_time_ms 在循环外定义）
                        if start_time_ms <= ts <= end_time_ms:
                            filtered_points.append(point)
                        else:
                            time_out_of_range_count += 1
                    else:
                        # 如果时间戳解析失败，打印警告但保留该点
                        print(f"  ⚠️  时间戳解析失败: {point_timestamp}，保留该点")
                        filtered_points.append(point)
                else:
                    # 如果没有时间戳，也保留（可能是数据问题）
                    filtered_points.append(point)
            
            # 打印筛选结果（在 for 循环外）
            print(f"  时间范围内有 {len(filtered_points)} 个轨迹点")
            if time_out_of_range_count > 0:
                print(f"  时间范围外有 {time_out_of_range_count} 个轨迹点")
                
                # 显示时间范围外的示例时间
                if time_out_of_range_count > 0 and len(history_list) > len(filtered_points):
                    print(f"  时间范围外的轨迹点时间示例:")
                    count = 0
                    for point in history_list:
                        if count >= 3:
                            break
                        ts_raw = point.get('timestamp')
                        if ts_raw:
                            ts_val = parse_timestamp_to_ms(ts_raw)
                            if ts_val > 0 and not (start_time_ms <= ts_val <= end_time_ms):
                                dt = datetime.fromtimestamp(ts_val / 1000)
                                print(f"    {ts_raw} -> {dt.strftime('%Y-%m-%d %H:%M:%S')} (时间戳: {ts_val})")
                                count += 1
            
            # 添加筛选后的点到总列表（在 for 循环外）
            if filtered_points:
                all_track_points.extend(filtered_points)
            
            # 如果返回的轨迹点数量少于page_size，说明已经是最后一页（在 for 循环外）
            if len(history_list) < page_size:
                print(f"已到达最后一页（返回 {len(history_list)} 个点，小于 page_size {page_size}）")
                break
            
            # 增加页码，准备查询下一页（在 for 循环外）
            page_no += 1
        else:
            print(f"第 {page_no} 页返回数据格式不正确")
            print(f"返回数据类型: {type(result)}")
            if isinstance(result, dict):
                print(f"返回数据键: {list(result.keys())}")
            elif isinstance(result, list):
                print(f"返回列表长度: {len(result)}")
            break
    
    # 显示汇总信息
    print(f"\n" + "=" * 60)
    print("查询汇总")
    print("=" * 60)
    print(f"查询页数: {page_no - 1}")
    print(f"收集到的轨迹点总数（筛选前）: {len(all_track_points)}")
    print(f"时间范围: {start_time_str} 到 {end_time_str}")
    
    # 如果没有收集到任何轨迹点，显示详细信息
    if not all_track_points:
        print("\n" + "=" * 60)
        print("⚠️  没有找到符合条件的轨迹点")
        print("=" * 60)
        print(f"查询时间范围: {start_time_str} 到 {end_time_str}")
        print(f"设备序列号: {sn}")
        print(f"查询了 {page_no - 1} 页数据")
        
        if page_no == 1:
            print("\n可能的原因:")
            print("1. API返回的historyList为空 - 该设备可能没有历史轨迹数据")
            print(f"2. 所有轨迹点的时间都在{DEFAULT_QUERY_DAYS}天之前 - 可以尝试查询更大的时间范围")
            print("3. Token已过期或设备序列号不正确")
            print("\n建议:")
            print("- 尝试查询更大的时间范围（如90天、180天）")
            print("- 检查设备是否有历史轨迹数据")
            print("- 验证token和设备序列号是否正确")
        else:
            print("\n可能的原因:")
            print("1. 所有轨迹点的时间都在查询时间范围之外")
            print(f"2. 设备在最近{DEFAULT_QUERY_DAYS}天内没有产生轨迹数据")
            print("\n建议:")
            print("- 尝试查询更大的时间范围（如90天、180天）")
            print("- 检查设备最后更新时间")
        
        return None
    
    if not all_track_points:
        print("\n" + "=" * 60)
        print("⚠️  没有找到符合条件的轨迹点")
        print("=" * 60)
        print(f"查询时间范围: {datetime.fromtimestamp(start_time/1000)} 到 {datetime.fromtimestamp(end_time/1000)}")
        print(f"设备序列号: {sn}")
        print("\n可能的原因:")
        print("1. 该设备在指定时间范围内没有历史轨迹数据")
        print("2. API返回的historyList为空或没有数据")
        print("3. 时间戳格式不匹配")
        print("\n建议:")
        print("- 尝试查询更大的时间范围（如7天、30天）")
        print("- 检查设备是否有历史轨迹数据")
        print("- 查看API返回的原始数据（可以设置verbose=True查看）")
        return None
    
    # 去重：根据时间戳和坐标去重
    print(f"\n去重前: {len(all_track_points)} 个轨迹点")
    unique_points = {}
    
    for point in all_track_points:
        timestamp = point.get('timestamp')
        latitude = point.get('latitude')
        longitude = point.get('longitude')
        
        # 使用时间戳+坐标作为唯一键
        if timestamp and latitude is not None and longitude is not None:
            try:
                ts = parse_timestamp_to_ms(timestamp)
                if ts > 0:
                    # 使用时间戳（精确到分钟）+坐标（保留3位小数）作为唯一键
                    ts_minute = ts // (60 * 1000)  # 精确到分钟
                    lat_rounded = round(float(latitude), 3)
                    lng_rounded = round(float(longitude), 3)
                    
                    unique_key = f"{ts_minute}_{lat_rounded}_{lng_rounded}"
                    
                    if unique_key not in unique_points:
                        unique_points[unique_key] = point
                else:
                    # 如果时间戳解析失败，也保留
                    unique_points[f"unknown_{len(unique_points)}"] = point
            except (ValueError, TypeError) as e:
                # 如果无法解析，也保留
                unique_points[f"unknown_{len(unique_points)}"] = point
    
    deduplicated_points = list(unique_points.values())
    
    # 按时间戳排序
    try:
        deduplicated_points.sort(key=lambda x: parse_timestamp_to_ms(x.get('timestamp', 0)))
    except Exception as e:
        # 如果排序失败，保持原顺序
        pass
    
    print(f"去重后: {len(deduplicated_points)} 个轨迹点")
    
    # 构建输出数据
    output_data = {
        'device_info': device_info,
        'query_info': {
            'sn': sn,
            'start_time': start_time_ms,
            'end_time': end_time_ms,
            'start_time_str': start_time_str,
            'end_time_str': end_time_str,
            'time_range_days': DEFAULT_QUERY_DAYS,
            'query_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_points_before_dedup': len(all_track_points),
            'total_points_after_dedup': len(deduplicated_points),
            'pages_queried': page_no - 1
        },
        'track_points': deduplicated_points
    }
    
    # 保存到JSON文件
    try:
        # 如果文件已存在，尝试合并
        if os.path.exists(output_file):
            print(f"\n检测到已存在的文件: {output_file}")
            merge_choice = input("是否合并到现有文件? (y/n，默认y): ").strip().lower()
            
            if merge_choice != 'n':
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                
                # 合并轨迹点
                existing_points = existing_data.get('track_points', [])
                combined_points = existing_points + deduplicated_points
                
                # 再次去重
                combined_unique = {}
                for point in combined_points:
                    timestamp = point.get('timestamp')
                    latitude = point.get('latitude')
                    longitude = point.get('longitude')
                    
                    if timestamp and latitude is not None and longitude is not None:
                        try:
                            ts = parse_timestamp_to_ms(timestamp)
                            if ts > 0:
                                ts_minute = ts // (60 * 1000)
                                lat_rounded = round(float(latitude), 3)
                                lng_rounded = round(float(longitude), 3)
                                unique_key = f"{ts_minute}_{lat_rounded}_{lng_rounded}"
                                
                                if unique_key not in combined_unique:
                                    combined_unique[unique_key] = point
                            else:
                                # 如果时间戳解析失败，使用备用键
                                combined_unique[f"unknown_{len(combined_unique)}"] = point
                        except Exception as e:
                            # 如果处理失败，使用备用键
                            combined_unique[f"unknown_{len(combined_unique)}"] = point
                
                merged_points = list(combined_unique.values())
                merged_points.sort(key=lambda x: parse_timestamp_to_ms(x.get('timestamp', 0)))
                
                output_data['track_points'] = merged_points
                output_data['query_info']['total_points_after_dedup'] = len(merged_points)
                output_data['query_info']['merged_from_existing'] = len(existing_points)
                
                print(f"合并完成: 原有 {len(existing_points)} 个点，新增 {len(deduplicated_points)} 个点，合并后 {len(merged_points)} 个点")
        
        # 保存 JSON 文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        file_path = os.path.abspath(output_file)
        print(f"\n✅ JSON 数据已保存到: {file_path}")
        print(f"   总轨迹点数: {len(output_data['track_points'])}")
        
        # 同时生成 JS 文件（可以直接通过 script 标签引用）
        js_file = 'history_tracks_data.js'
        try:
            js_content = '// 自动生成的轨迹数据文件（从 ' + output_file + ' 生成）\n'
            js_content += '// 此文件由 query_tracks.py 自动生成，请勿手动编辑\n'
            js_content += '// 生成时间: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n\n'
            js_content += 'const trackData = ' + json.dumps(output_data, ensure_ascii=False, indent=2) + ';\n'
            
            with open(js_file, 'w', encoding='utf-8') as f:
                f.write(js_content)
            
            js_file_path = os.path.abspath(js_file)
            print(f"✅ JS 数据已保存到: {js_file_path}")
            print(f"   现在可以通过 <script src=\"{js_file}\"></script> 在 HTML 中引用")
        except Exception as e:
            print(f"⚠️  生成 JS 文件失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 显示统计信息
        if output_data['track_points']:
            first_point = output_data['track_points'][0]
            last_point = output_data['track_points'][-1]
            first_time = first_point.get('timestamp')
            last_time = last_point.get('timestamp')
            
            if first_time and last_time:
                try:
                    first_ts = int(first_time) if isinstance(first_time, str) else int(first_time)
                    last_ts = int(last_time) if isinstance(last_time, str) else int(last_time)
                    if first_ts < 1000000000000:
                        first_ts *= 1000
                    if last_ts < 1000000000000:
                        last_ts *= 1000
                    
                    first_dt = datetime.fromtimestamp(first_ts / 1000)
                    last_dt = datetime.fromtimestamp(last_ts / 1000)
                    time_span = (last_ts - first_ts) / 1000 / 3600
                    
                    print(f"   时间范围: {first_dt.strftime('%Y-%m-%d %H:%M:%S')} 到 {last_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   时间跨度: {time_span:.2f} 小时 ({time_span/24:.2f} 天)")
                except:
                    pass
        
        return output_data
        
    except Exception as e:
        print(f"\n❌ 保存文件失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_history_track_points(token: str, uid: int, sn: str = None,
                            start_time: int = None, end_time: int = None,
                            page_no: int = 1, page_size: int = 20,
                            verbose: bool = True) -> dict:
    """
    获取设备在指定时间范围内的历史轨迹点
    
    Args:
        token: 用户 token
        uid: 用户 ID
        sn: 设备序列号（必需）
        start_time: 开始时间戳（毫秒），用于筛选历史轨迹点
        end_time: 结束时间戳（毫秒），用于筛选历史轨迹点
        page_no: 页码（默认1）
        page_size: 每页大小（默认20，可以增大以获取更多数据）
        verbose: 是否打印详细信息
    
    Returns:
        包含历史轨迹点的响应数据，如果失败返回 None
    
    注意：根据API实际行为，查询历史轨迹点使用 sn + 分页参数（pageNo + pageSize）。
         时间范围在客户端筛选 historyList。
         可以增大 page_size 以获取更多历史轨迹点。
    """
    # 如果没有提供时间范围，使用默认值（最近6小时）
    if end_time is None:
        end_time = int(datetime.now().timestamp() * 1000)
    if start_time is None:
        start_time = end_time - 6 * 60 * 60 * 1000  # 6小时前
    
    # 如果时间范围较大，建议增大 page_size 以获取更多数据
    time_range_days = (end_time - start_time) / 1000 / 3600 / 24
    if time_range_days > 7:
        if page_size < 50:
            suggested_page_size = min(100, max(50, int(page_size * (time_range_days / 7))))
            if verbose:
                print(f"⚠️  时间范围较大（{time_range_days:.1f}天），建议增大 page_size 以获取更多数据")
                print(f"   当前 page_size: {page_size}，建议: {suggested_page_size}")
        elif verbose:
            print(f"ℹ️  时间范围: {time_range_days:.1f}天，当前 page_size: {page_size}")
    
    if verbose:
        print("=" * 60)
        print("获取历史轨迹点")
        print("=" * 60)
        print(f"设备序列号: {sn}")
        print(f"筛选时间范围: {datetime.fromtimestamp(start_time/1000)} 到 {datetime.fromtimestamp(end_time/1000)}")
        time_range_hours = (end_time - start_time) / 1000 / 3600
        if time_range_hours < 24:
            print(f"时间范围: {time_range_hours:.2f} 小时")
        else:
            print(f"时间范围: {time_range_hours / 24:.2f} 天")
        print(f"分页参数: pageNo={page_no}, pageSize={page_size}")
        print("\n注意: 使用 sn + 分页参数查询指定设备，时间范围在客户端筛选")
        print(f"提示: 如果时间范围较大，可以增大 page_size 以获取更多历史轨迹点")
    
    # 发送请求并解密
    # 使用 sn + 分页参数查询指定设备（时间范围在客户端筛选）
    result = call_and_decrypt_api(
        token=token,
        uid=uid,
        sn=sn,  # 使用sn参数查询指定设备
        start_time=None,  # 不使用时间范围参数（在客户端筛选）
        end_time=None,
        page_no=page_no,
        page_size=page_size
    )
    
    # 确保返回的是指定设备的数据
    if result:
        if isinstance(result, list):
            # 筛选指定设备的数据
            filtered_result = [device for device in result if device.get('sn') == sn]
            if filtered_result:
                result = filtered_result
            else:
                if verbose:
                    print(f"\n⚠️  未找到设备序列号为 {sn} 的设备")
                return None
        elif isinstance(result, dict) and result.get('sn') != sn:
            if verbose:
                print(f"\n⚠️  返回的设备序列号 {result.get('sn')} 与请求的 {sn} 不匹配")
            return None
    
    if result and (start_time or end_time):
        # 筛选时间范围内的历史轨迹点
        if isinstance(result, list):
            for device in result:
                history_list = device.get('historyList', [])
                if history_list:
                    filtered_history = []
                    for point in history_list:
                        point_timestamp = point.get('timestamp')
                        if point_timestamp:
                            try:
                                # timestamp 可能是字符串或数字
                                if isinstance(point_timestamp, str):
                                    point_ts = int(point_timestamp)
                                else:
                                    point_ts = int(point_timestamp)
                                
                                # 如果 timestamp 是秒级时间戳，转换为毫秒
                                if point_ts < 1000000000000:
                                    point_ts = point_ts * 1000
                                
                                if start_time <= point_ts <= end_time:
                                    filtered_history.append(point)
                            except (ValueError, TypeError):
                                # 如果时间戳解析失败，保留该点
                                filtered_history.append(point)
                    
                    device['historyList'] = filtered_history
                    
                    if verbose:
                        print(f"\n设备 {device.get('sn', '未知')}: 筛选前 {len(history_list)} 个点，筛选后 {len(filtered_history)} 个点")
                        
                        # 显示时间范围信息
                        if filtered_history:
                            first_point_time = filtered_history[0].get('timestamp')
                            last_point_time = filtered_history[-1].get('timestamp')
                            if first_point_time and last_point_time:
                                try:
                                    first_ts = int(first_point_time) if isinstance(first_point_time, str) else int(first_point_time)
                                    last_ts = int(last_point_time) if isinstance(last_point_time, str) else int(last_point_time)
                                    if first_ts < 1000000000000:
                                        first_ts *= 1000
                                    if last_ts < 1000000000000:
                                        last_ts *= 1000
                                    
                                    first_dt = datetime.fromtimestamp(first_ts / 1000)
                                    last_dt = datetime.fromtimestamp(last_ts / 1000)
                                    print(f"   轨迹点时间范围: {first_dt.strftime('%Y-%m-%d %H:%M:%S')} 到 {last_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                                except:
                                    pass
    
    if result and verbose:
        # 解析历史轨迹点
        if isinstance(result, list) and len(result) > 0:
            device_info = result[0]
            history_list = device_info.get('historyList', [])
            
            print("\n" + "=" * 60)
            print(f"设备信息: {device_info.get('name', '未知设备')}")
            print(f"设备序列号: {device_info.get('sn', '未知')}")
            print(f"历史轨迹点数量: {len(history_list)}")
            print("=" * 60)
            
            if history_list:
                print("\n历史轨迹点详情:")
                print("-" * 60)
                
                # 如果轨迹点太多，只显示前10个和后10个
                display_count = 10
                if len(history_list) > display_count * 2:
                    print(f"（显示前 {display_count} 个和后 {display_count} 个轨迹点，共 {len(history_list)} 个）")
                    print("\n前 {} 个轨迹点:".format(display_count))
                    for i, point in enumerate(history_list[:display_count], 1):
                        _print_track_point(point, i)
                    
                    print(f"\n... (省略中间 {len(history_list) - display_count * 2} 个轨迹点) ...\n")
                    
                    print(f"后 {display_count} 个轨迹点:")
                    for i, point in enumerate(history_list[-display_count:], len(history_list) - display_count + 1):
                        _print_track_point(point, i)
                else:
                    for i, point in enumerate(history_list, 1):
                        _print_track_point(point, i)
                
                # 显示统计信息
                print("\n" + "-" * 60)
                print("统计信息:")
                print(f"  总轨迹点数: {len(history_list)}")
                if history_list:
                    try:
                        timestamps = []
                        for point in history_list:
                            ts = point.get('timestamp')
                            if ts:
                                ts_val = int(ts) if isinstance(ts, str) else int(ts)
                                if ts_val < 1000000000000:
                                    ts_val *= 1000
                                timestamps.append(ts_val)
                        
                        if timestamps:
                            timestamps.sort()
                            first_time = datetime.fromtimestamp(timestamps[0] / 1000)
                            last_time = datetime.fromtimestamp(timestamps[-1] / 1000)
                            time_span = (timestamps[-1] - timestamps[0]) / 1000 / 3600
                            
                            print(f"  最早轨迹点: {first_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"  最晚轨迹点: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"  时间跨度: {time_span:.2f} 小时 ({time_span/24:.2f} 天)")
                    except:
                        pass
            else:
                print("\n⚠️  该时间范围内没有历史轨迹点")
                print("提示: 可以尝试:")
                print("  1. 增大时间范围")
                print("  2. 增大 page_size 参数")
                print("  3. 检查设备是否有历史轨迹数据")
        else:
            print("\n⚠️  返回的数据格式不正确或为空")
    
    return result


def parse_history_points(result: dict) -> list:
    """
    从 API 响应中解析历史轨迹点列表
    
    Args:
        result: API 返回的解密后的数据
    
    Returns:
        历史轨迹点列表，如果解析失败返回空列表
    """
    if not result:
        return []
    
    if isinstance(result, list) and len(result) > 0:
        device_info = result[0]
        history_list = device_info.get('historyList', [])
        return history_list if history_list else []
    
    return []


def export_history_points_to_json(history_points: list, sn: str, 
                                  start_time: int = None, end_time: int = None,
                                  filename: str = None) -> str:
    """
    将历史轨迹点导出为 JSON 文件
    
    Args:
        history_points: 历史轨迹点列表
        sn: 设备序列号
        start_time: 开始时间戳（可选）
        end_time: 结束时间戳（可选）
        filename: 文件名（可选，如果不提供则自动生成）
    
    Returns:
        保存的文件路径
    """
    if filename is None:
        timestamp = int(datetime.now().timestamp())
        filename = f"history_track_{sn}_{timestamp}.json"
    
    export_data = {
        'device_sn': sn,
        'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'point_count': len(history_points),
        'start_time': start_time,
        'end_time': end_time,
        'history_points': history_points
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    return filename


def get_token_and_uid(force_login: bool = False) -> tuple:
    """
    获取 token 和 uid，优先从文件读取，如果没有则提示登录
    
    Args:
        force_login: 是否强制重新登录（忽略保存的 token）
    
    Returns:
        (token, uid) 元组，如果获取失败返回 (None, None)
    """
    token = None
    uid = None
    
    # 如果不是强制登录，先尝试从文件读取
    if not force_login:
        token, uid, saved_username = load_token_from_file()
        if token and uid:
            print(f"✅ 从文件读取到保存的 token (用户ID: {uid})")
            if saved_username:
                print(f"   用户名: {saved_username}")
            return token, uid
    
    # 如果没有保存的 token 或强制登录，则提示登录
    print("\n需要登录获取 token")
    print("-" * 60)
    
    username_input = input("请输入用户名 (直接回车使用默认值): ").strip()
    password_input = input("请输入密码 (直接回车使用默认值): ").strip()
    
    username = username_input if username_input else None
    password = password_input if password_input else None
    
    token, uid = login_and_get_token(username, password, save_token=True)
    
    return token, uid


def main():
    """示例用法"""
    # 注意：快捷查询提示已在 if __name__ == "__main__" 中处理
    print("=" * 60)
    print("CityTag API 请求体生成工具")
    print("=" * 60)
    
    # 示例 1: 设备轨迹查询
    print("\n【示例 1】设备轨迹查询")
    print("-" * 60)
    token = "your_user_token_here"  # 替换为实际的用户 token
    uid = 242487
    sn = DEFAULT_DEVICE_SN
    start_time = 1609459200000  # 时间戳（毫秒）
    end_time = 1609545600000
    
    request_body_1 = generate_request_body(
        token=token,
        uid=uid,
        sn=sn,
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"Token: {token}")
    print(f"业务数据: uid={uid}, sn={sn}, startTime={start_time}, endTime={end_time}")
    print(f"请求体 JSON:")
    print(json.dumps(request_body_1, indent=2, ensure_ascii=False))
    
    # 示例 2: 分页查询
    print("\n【示例 2】分页查询")
    print("-" * 60)
    request_body_2 = generate_request_body(
        token=token,
        uid=uid,
        page_no=1,
        page_size=20
    )
    
    print(f"业务数据: uid={uid}, pageNo=1, pageSize=20")
    print(f"请求体 JSON:")
    print(json.dumps(request_body_2, indent=2, ensure_ascii=False))
    
    # 示例 3: Token 管理
    print("\n【示例 3】Token 管理")
    print("-" * 60)
    print("Token 存储文件位置:", TOKEN_FILE)
    
    # 检查是否有保存的 token
    saved_token, saved_uid, saved_username = load_token_from_file()
    if saved_token:
        print(f"✅ 已保存的 token:")
        print(f"   用户ID: {saved_uid}")
        if saved_username:
            print(f"   用户名: {saved_username}")
    else:
        print("ℹ️  暂无保存的 token")
    
    print("\nToken 管理函数:")
    print("  - save_token_to_file(token, uid, username): 保存 token")
    print("  - load_token_from_file(): 读取 token")
    print("  - clear_token_file(): 清除保存的 token")
    print("  - get_token_and_uid(): 自动获取 token（优先从文件读取）")
    
    # 示例 4: 解密 API 响应
    print("\n【示例 4】解密 API 响应")
    print("-" * 60)
    print("示例: 解密接口返回的加密数据")
    encrypted_response_data = "示例加密的Base64字符串"
    print(f"加密数据: {encrypted_response_data}")
    print("解密代码:")
    print("  from generate_request_body import decrypt_api_response")
    print("  decrypted = decrypt_api_response(token, encrypted_response_data)")
    print("  print(json.dumps(decrypted, indent=2, ensure_ascii=False))")
    
    # 示例 5: 通过登录获取 token（演示）
    print("\n【示例 5】通过登录获取 token")
    print("-" * 60)
    print("提示: Token 会自动保存到文件，下次使用时可以直接读取")
    print("注意: 需要先安装 requests 库: pip install requests")
    
    # 示例 6: 生成请求体并发送请求、解密响应
    print("\n【示例 5】生成请求体并发送请求、解密响应")
    print("-" * 60)
    
    if not HAS_REQUESTS:
        print("⚠️  需要安装 requests 库才能发送请求")
        print("请运行: pip install requests")
    else:
        # 自动获取 token（优先从文件读取）
        demo_token, demo_uid = get_token_and_uid(force_login=False)
        
        if demo_token:
            print(f"\n✅ 获取到 token，开始发送请求...")
            
            # 示例：获取不同时间范围的历史轨迹点
            demo_sn = DEFAULT_DEVICE_SN  # 使用默认设备序列号
            
            # 测试不同的时间范围
            print("\n测试不同的时间范围:")
            print("1. 6小时内")
            print("2. 3天内")
            print("3. 7天内")
            print("4. 30天内")
            print("5. 90天内")
            
            test_choice = input("请选择测试的时间范围 (1-5，直接回车测试6小时内): ").strip()
            
            end_time = int(datetime.now().timestamp() * 1000)
            
            if test_choice == "2":
                start_time = end_time - 3 * 24 * 60 * 60 * 1000
                page_size = 50  # 增大 page_size 以获取更多数据
            elif test_choice == "3":
                start_time = end_time - 7 * 24 * 60 * 60 * 1000
                page_size = 100  # 进一步增大 page_size
            elif test_choice == "4":
                start_time = end_time - 30 * 24 * 60 * 60 * 1000
                page_size = 100  # 使用较大的 page_size
            elif test_choice == "5":
                start_time = end_time - 90 * 24 * 60 * 60 * 1000
                page_size = 100  # 使用较大的 page_size
            else:
                start_time = end_time - 6 * 60 * 60 * 1000
                page_size = 20
            
            # 发送请求并解密
            result = get_history_track_points(
                token=demo_token,
                uid=demo_uid,
                sn=demo_sn,
                start_time=start_time,
                end_time=end_time,
                page_no=1,
                page_size=page_size,
                verbose=True
            )
            
            if result:
                print("\n✅ 请求完成！")
            else:
                print("\n❌ 请求失败！")
        else:
            print("\n⚠️  无法获取 token，跳过请求示例")
    
    # 示例 7: 获取历史轨迹点
    print("\n【示例 7】获取历史轨迹点")
    print("-" * 60)
    
    if not HAS_REQUESTS:
        print("⚠️  需要安装 requests 库才能发送请求")
        print("请运行: pip install requests")
    else:
        # 自动获取 token（优先从文件读取）
        demo_token, demo_uid = get_token_and_uid(force_login=False)
        
        if demo_token:
            print(f"\n✅ 获取到 token，开始获取历史轨迹点...")
            
            # 示例：获取6小时内的历史轨迹点
            demo_sn = DEFAULT_DEVICE_SN  # 使用默认设备序列号
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - 6 * 60 * 60 * 1000
            
            result = get_history_track_points(
                token=demo_token,
                uid=demo_uid,
                sn=demo_sn,
                start_time=start_time,
                end_time=end_time,
                verbose=True
            )
            
            if result:
                # 解析历史轨迹点
                history_points = parse_history_points(result)
                if history_points:
                    print(f"\n✅ 成功获取 {len(history_points)} 个历史轨迹点")
                    
                    # 询问是否导出
                    export_choice = input("\n是否导出历史轨迹点为 JSON 文件? (y/n): ").strip().lower()
                    if export_choice == 'y':
                        filename = export_history_points_to_json(
                            history_points=history_points,
                            sn=demo_sn,
                            start_time=start_time,
                            end_time=end_time
                        )
                        print(f"✅ 历史轨迹点已导出到: {filename}")
                else:
                    print("\n⚠️  该时间范围内没有历史轨迹点")
            else:
                print("\n❌ 获取历史轨迹点失败！")
        else:
            print("\n⚠️  无法获取 token，跳过历史轨迹点示例")
    
    # 示例 8: 交互式输入
    print("\n【示例 8】交互式输入（生成请求体并发送）")
    print("-" * 60)
    try:
        # 先尝试从文件读取 token
        user_token, user_uid, saved_username = load_token_from_file()
        
        if user_token and user_uid:
            print(f"✅ 检测到保存的 token (用户ID: {user_uid})")
            use_saved = input("是否使用保存的 token? (y/n，默认y): ").strip().lower()
            
            if use_saved != 'n':
                print("使用保存的 token")
            else:
                # 询问是否要重新登录
                login_choice = input("是否重新登录获取 token? (y/n，直接回车使用已有token): ").strip().lower()
                
                if login_choice == 'y':
                    username_input = input("请输入用户名 (直接回车使用默认值): ").strip()
                    password_input = input("请输入密码 (直接回车使用默认值): ").strip()
                    
                    username = username_input if username_input else None
                    password = password_input if password_input else None
                    
                    user_token, user_uid = login_and_get_token(username, password, save_token=True)
                    if user_token is None:
                        print("登录失败，退出")
                        return
                else:
                    user_token = input("请输入用户 token: ").strip()
                    user_uid_input = input("请输入用户 ID: ").strip()
                    if not user_uid_input:
                        print("用户 ID 不能为空")
                        return
                    user_uid = int(user_uid_input)
        else:
            # 没有保存的 token，需要登录或输入
            login_choice = input("是否通过登录获取 token? (y/n，直接回车使用已有token): ").strip().lower()
            
            if login_choice == 'y':
                username_input = input("请输入用户名 (直接回车使用默认值): ").strip()
                password_input = input("请输入密码 (直接回车使用默认值): ").strip()
                
                username = username_input if username_input else None
                password = password_input if password_input else None
                
                user_token, user_uid = login_and_get_token(username, password, save_token=True)
                if user_token is None:
                    print("登录失败，退出")
                    return
            else:
                user_token = input("请输入用户 token: ").strip()
                user_uid_input = input("请输入用户 ID: ").strip()
                if not user_uid_input:
                    print("用户 ID 不能为空")
                    return
                user_uid = int(user_uid_input)
        
        if not HAS_REQUESTS:
            print("\n⚠️  需要安装 requests 库才能发送请求")
            print("请运行: pip install requests")
            return
        
        # 询问查询类型
        query_type = input("请选择查询类型 (1=历史轨迹点, 2=分页查询): ").strip()
        
        if query_type == "1":
            # 历史轨迹点查询
            device_sn_input = input(f"请输入设备序列号 (sn，直接回车使用默认值 {DEFAULT_DEVICE_SN}): ").strip()
            device_sn = device_sn_input if device_sn_input else DEFAULT_DEVICE_SN
            print(f"使用设备序列号: {device_sn}")
            
            # 时间范围选择
            time_range_choice = input("时间范围选择 (1=6小时内, 2=3天内, 3=7天内, 4=30天内, 5=90天内, 6=自定义): ").strip()
            
            end_time_val = int(datetime.now().timestamp() * 1000)
            
            if time_range_choice == "1":
                # 6小时内
                start_time_val = end_time_val - 6 * 60 * 60 * 1000
            elif time_range_choice == "2":
                # 3天内
                start_time_val = end_time_val - 3 * 24 * 60 * 60 * 1000
            elif time_range_choice == "3":
                # 7天内
                start_time_val = end_time_val - 7 * 24 * 60 * 60 * 1000
            elif time_range_choice == "4":
                # 30天内
                start_time_val = end_time_val - 30 * 24 * 60 * 60 * 1000
            elif time_range_choice == "5":
                # 90天内
                start_time_val = end_time_val - 90 * 24 * 60 * 60 * 1000
            elif time_range_choice == "6":
                # 自定义时间范围
                start_date_str = input("请输入开始日期 (格式: YYYY-MM-DD，例如: 2024-01-01): ").strip()
                end_date_str = input("请输入结束日期 (格式: YYYY-MM-DD，例如: 2024-01-02): ").strip()
                
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                    
                    start_time_val = int(start_date.timestamp() * 1000)
                    end_time_val = int((end_date + timedelta(days=1)).timestamp() * 1000) - 1
                except ValueError as e:
                    print(f"日期格式错误: {e}")
                    return
            else:
                # 默认6小时内
                end_time_val = int(datetime.now().timestamp() * 1000)
                start_time_val = end_time_val - 6 * 60 * 60 * 1000
            
            if verbose:
                time_range_days = (end_time_val - start_time_val) / 1000 / 3600 / 24
                print(f"\n查询时间范围: {time_range_days:.2f} 天")
            
            # 根据时间范围调整 page_size
            time_range_days = (end_time_val - start_time_val) / 1000 / 3600 / 24
            if time_range_days > 30:
                suggested_page_size = 100
            elif time_range_days > 7:
                suggested_page_size = 100
            elif time_range_days > 3:
                suggested_page_size = 50
            else:
                suggested_page_size = 20
            
            print(f"\n时间范围: {time_range_days:.2f} 天")
            page_size_input = input(f"请输入每页大小 (建议 {suggested_page_size}，直接回车使用建议值): ").strip()
            page_size_val = int(page_size_input) if page_size_input else suggested_page_size
            
            # 如果用户输入了更大的值，也可以支持
            if page_size_val > 100:
                confirm = input(f"⚠️  page_size={page_size_val} 较大，是否继续? (y/n，默认y): ").strip().lower()
                if confirm == 'n':
                    page_size_val = 100
                    print(f"已调整为 page_size={page_size_val}")
            
            # 获取历史轨迹点（使用分页参数）
            result = get_history_track_points(
                token=user_token,
                uid=user_uid,
                sn=device_sn,
                start_time=start_time_val,
                end_time=end_time_val,
                page_no=1,
                page_size=page_size_val,
                verbose=True
            )
            
            if result:
                # 解析历史轨迹点
                history_points = parse_history_points(result)
                if history_points:
                    print(f"\n✅ 成功获取 {len(history_points)} 个历史轨迹点")
                    
                    # 询问是否导出
                    export_choice = input("\n是否导出历史轨迹点为 JSON 文件? (y/n): ").strip().lower()
                    if export_choice == 'y':
                        filename = export_history_points_to_json(
                            history_points=history_points,
                            sn=device_sn,
                            start_time=start_time_val,
                            end_time=end_time_val
                        )
                        print(f"✅ 历史轨迹点已导出到: {filename}")
        elif query_type == "2":
            # 分页查询
            device_sn_input = input(f"请输入设备序列号 (可选，直接回车使用默认值 {DEFAULT_DEVICE_SN}): ").strip()
            device_sn = device_sn_input if device_sn_input else DEFAULT_DEVICE_SN
            
            if device_sn:
                # 设备轨迹查询（不使用历史轨迹点功能）
                start = input("请输入开始时间戳 (可选，直接回车使用默认值1): ").strip()
                end = input("请输入结束时间戳 (可选，直接回车使用默认值1): ").strip()
                
                start_time_val = int(start) if start else None
                end_time_val = int(end) if end else None
                
                # 发送请求并解密
                result = call_and_decrypt_api(
                    token=user_token,
                    uid=user_uid,
                    sn=device_sn,
                    start_time=start_time_val,
                    end_time=end_time_val
                )
            else:
                # 分页查询
                page_no_input = input("请输入页码 (可选，默认1): ").strip()
                page_size_input = input("请输入每页大小 (可选，默认20): ").strip()
                
                page_no_val = int(page_no_input) if page_no_input else 1
                page_size_val = int(page_size_input) if page_size_input else 20
                
                # 发送请求并解密
                result = call_and_decrypt_api(
                    token=user_token,
                    uid=user_uid,
                    page_no=page_no_val,
                    page_size=page_size_val
                )
        else:
            print("无效的查询类型")
            return
        
        if result:
            print("\n✅ 请求完成！")
        else:
            print("\n❌ 请求失败！")
        
        # 询问是否清除保存的 token
        if user_token:
            clear_choice = input("\n是否清除保存的 token? (y/n，默认n): ").strip().lower()
            if clear_choice == 'y':
                if clear_token_file():
                    print("✅ Token 文件已清除")
                else:
                    print("❌ Token 文件清除失败")
        
    except KeyboardInterrupt:
        print("\n\n已取消输入")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


def quick_query_main():
    """快捷查询主函数：查询指定天数内的数据并保存到JSON文件"""
    print("=" * 60)
    print(f"快捷查询：{DEFAULT_QUERY_DAYS}天内的历史轨迹点")
    print("=" * 60)
    
    # 使用默认值
    sn = DEFAULT_DEVICE_SN
    output_file = "history_tracks.json"
    
    print(f"使用默认设备序列号: {sn}")
    print(f"输出文件: {output_file}")
    print(f"时间范围: 最近{DEFAULT_QUERY_DAYS}天")
    print(f"所有参数使用默认值，自动查询并保存")
    
    # 执行快捷查询
    result = quick_query(sn=sn, output_file=output_file, max_pages=10)
    
    if result:
        print("\n" + "=" * 60)
        print("✅ 快捷查询完成！")
        print("=" * 60)
        print(f"文件位置: {os.path.abspath(output_file)}")
        print(f"总轨迹点数: {len(result.get('track_points', []))}")
    else:
        print("\n" + "=" * 60)
        print("❌ 快捷查询失败！")
        print("=" * 60)


if __name__ == "__main__":
    import sys
    
    # 如果命令行参数包含 "quick" 或 "fast"，执行快捷查询
    if len(sys.argv) > 1 and ('quick' in sys.argv[1].lower() or 'fast' in sys.argv[1].lower()):
        quick_query_main()
    else:
        # 在 main 函数开始前，询问是否执行快捷查询
        print("=" * 60)
        print("CityTag API 请求体生成工具")
        print("=" * 60)
        quick_choice = input(f"是否执行快捷查询（{DEFAULT_QUERY_DAYS}天内数据，使用默认值）? (y/n，默认n): ").strip().lower()
        
        if quick_choice == 'y':
            quick_query_main()
        else:
            main()
