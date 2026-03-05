#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的 API 调用示例
包括：登录获取 token、生成请求体、发送请求、解密响应

注意: 默认用户名和密码在 generate_request_body.py 中设置
"""

import json
import requests
from generate_request_body import (
    login_and_get_token,
    generate_request_body,
    decrypt_api_response
)

# 默认用户名和密码（如果 generate_request_body.py 中没有设置，可以在这里设置）
DEFAULT_USERNAME = None  # 设置为 None 会使用 generate_request_body.py 中的默认值
DEFAULT_PASSWORD = None  # 设置为 None 会使用 generate_request_body.py 中的默认值


def call_device3_api(token: str, uid: int, sn: str = None, 
                    start_time: int = None, end_time: int = None,
                    page_no: int = None, page_size: int = None):
    """
    调用 /api/interface/v2/device3/{uid} 接口
    
    Args:
        token: 用户 token
        uid: 用户 ID
        sn: 设备序列号（设备轨迹查询时需要）
        start_time: 开始时间戳（设备轨迹查询时需要）
        end_time: 结束时间戳（设备轨迹查询时需要）
        page_no: 页码（分页查询时需要）
        page_size: 每页大小（分页查询时需要）
    
    Returns:
        解密后的响应数据（字典）
    """
    # 1. 生成请求体
    request_body = generate_request_body(
        token=token,
        uid=uid,
        sn=sn,
        start_time=start_time,
        end_time=end_time,
        page_no=page_no,
        page_size=page_size
    )
    
    print("=" * 60)
    print("请求信息")
    print("=" * 60)
    print(f"URL: https://citytag.yuminstall.top/api/interface/v2/device3/{uid}")
    print(f"请求体:")
    print(json.dumps(request_body, indent=2, ensure_ascii=False))
    
    # 2. 发送请求
    url = f"https://citytag.yuminstall.top/api/interface/v2/device3/{uid}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "CityTag"
    }
    
    try:
        response = requests.post(url, json=request_body, headers=headers)
        response.raise_for_status()
        
        # 3. 解析响应
        response_data = response.json()
        
        print("\n" + "=" * 60)
        print("响应信息")
        print("=" * 60)
        print(f"状态码: {response.status_code}")
        print(f"响应码: {response_data.get('code')}")
        print(f"响应消息: {response_data.get('msg')}")
        
        # 4. 检查响应码
        if response_data.get('code') != '00000':
            print(f"错误: {response_data.get('msg')}")
            return None
        
        # 5. 解密响应数据
        encrypted_data = response_data.get('data')
        if not encrypted_data:
            print("响应中没有 data 字段")
            return None
        
        print(f"\n加密的 data 字段: {encrypted_data[:50]}...")
        print("\n开始解密...")
        
        decrypted_data = decrypt_api_response(token, encrypted_data)
        
        print("\n" + "=" * 60)
        print("解密后的数据")
        print("=" * 60)
        print(json.dumps(decrypted_data, indent=2, ensure_ascii=False))
        
        return decrypted_data
        
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None
    except Exception as e:
        print(f"处理错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数 - 演示完整流程"""
    print("=" * 60)
    print("CityTag API 完整调用示例")
    print("=" * 60)
    
    # 方式1: 使用已有的 token
    print("\n【方式1】使用已有的 token")
    print("-" * 60)
    token = input("请输入 token (直接回车跳过，使用登录方式): ").strip()
    uid = None
    
    if not token:
        # 方式2: 通过登录获取 token
        print("\n【方式2】通过登录获取 token")
        print("-" * 60)
        username_input = input("请输入用户名 (直接回车使用默认值): ").strip()
        password_input = input("请输入密码 (直接回车使用默认值): ").strip()
        
        # 如果输入为空，使用 None 让函数使用默认值
        username = username_input if username_input else None
        password = password_input if password_input else None
        
        token, uid = login_and_get_token(username, password)
        if token is None:
            print("登录失败，退出")
            return
    
    if uid is None:
        uid_input = input("请输入用户 ID: ").strip()
        if uid_input:
            uid = int(uid_input)
        else:
            print("用户 ID 不能为空")
            return
    
    # 选择查询类型
    print("\n请选择查询类型:")
    print("1. 设备轨迹查询（需要 sn、startTime、endTime）")
    print("2. 分页查询（需要 pageNo、pageSize）")
    
    query_type = input("请输入选项 (1 或 2): ").strip()
    
    if query_type == "1":
        # 设备轨迹查询
        sn = input("请输入设备序列号 (sn): ").strip()
        start_time_input = input("请输入开始时间戳 (可选，直接回车使用默认值1): ").strip()
        end_time_input = input("请输入结束时间戳 (可选，直接回车使用默认值1): ").strip()
        
        start_time = int(start_time_input) if start_time_input else None
        end_time = int(end_time_input) if end_time_input else None
        
        result = call_device3_api(
            token=token,
            uid=uid,
            sn=sn,
            start_time=start_time,
            end_time=end_time
        )
        
    elif query_type == "2":
        # 分页查询
        page_no_input = input("请输入页码 (pageNo，默认1): ").strip()
        page_size_input = input("请输入每页大小 (pageSize，默认20): ").strip()
        
        page_no = int(page_no_input) if page_no_input else 1
        page_size = int(page_size_input) if page_size_input else 20
        
        result = call_device3_api(
            token=token,
            uid=uid,
            page_no=page_no,
            page_size=page_size
        )
    else:
        print("无效的选项")
        return
    
    if result:
        print("\n✅ API 调用成功！")
    else:
        print("\n❌ API 调用失败！")


if __name__ == "__main__":
    main()
