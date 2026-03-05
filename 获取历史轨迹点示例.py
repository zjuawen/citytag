#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取历史轨迹点的示例
演示如何获取设备在指定时间范围内的多个历史轨迹点
"""

import json
from datetime import datetime, timedelta
from generate_request_body import (
    get_token_and_uid,
    call_and_decrypt_api,
    generate_request_body,
    decrypt_api_response
)


def get_timestamp_ms(year, month, day, hour=0, minute=0, second=0):
    """
    将日期时间转换为毫秒时间戳
    
    Args:
        year, month, day, hour, minute, second: 日期时间
    
    Returns:
        毫秒时间戳
    """
    dt = datetime(year, month, day, hour, minute, second)
    return int(dt.timestamp() * 1000)


def get_history_track_points(token: str, uid: int, sn: str, 
                            start_time: int, end_time: int):
    """
    获取设备在指定时间范围内的历史轨迹点
    
    Args:
        token: 用户 token
        uid: 用户 ID
        sn: 设备序列号
        start_time: 开始时间戳（毫秒）
        end_time: 结束时间戳（毫秒）
    
    Returns:
        解密后的响应数据，包含历史轨迹点列表
    """
    print("=" * 60)
    print("获取历史轨迹点")
    print("=" * 60)
    print(f"设备序列号: {sn}")
    print(f"开始时间: {datetime.fromtimestamp(start_time/1000)}")
    print(f"结束时间: {datetime.fromtimestamp(end_time/1000)}")
    print(f"时间范围: {(end_time - start_time) / 1000 / 3600:.2f} 小时")
    
    # 发送请求并解密
    result = call_and_decrypt_api(
        token=token,
        uid=uid,
        sn=sn,
        start_time=start_time,
        end_time=end_time
    )
    
    if result:
        # 解析历史轨迹点
        if isinstance(result, list) and len(result) > 0:
            device_info = result[0]
            history_list = device_info.get('historyList', [])
            
            print("\n" + "=" * 60)
            print(f"设备信息: {device_info.get('name', '未知设备')}")
            print(f"历史轨迹点数量: {len(history_list)}")
            print("=" * 60)
            
            if history_list:
                print("\n历史轨迹点详情:")
                print("-" * 60)
                for i, point in enumerate(history_list, 1):
                    print(f"\n点 {i}:")
                    print(f"  纬度: {point.get('latitude')}")
                    print(f"  经度: {point.get('longitude')}")
                    print(f"  时间戳: {point.get('timestamp')}")
                    if point.get('timestamp'):
                        try:
                            ts = int(point.get('timestamp')) / 1000
                            dt = datetime.fromtimestamp(ts)
                            print(f"  时间: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                        except:
                            pass
                    print(f"  精度: {point.get('accuracy', 'N/A')}")
                    print(f"  置信度: {point.get('confidence', 'N/A')}")
                    print(f"  更新时间: {point.get('updatetime', 'N/A')}")
            else:
                print("\n⚠️  该时间范围内没有历史轨迹点")
        else:
            print("\n⚠️  返回的数据格式不正确或为空")
    
    return result


def main():
    """主函数"""
    print("=" * 60)
    print("获取历史轨迹点示例")
    print("=" * 60)
    
    # 获取 token（优先从文件读取）
    token, uid = get_token_and_uid(force_login=False)
    
    if not token:
        print("❌ 无法获取 token，退出")
        return
    
    print(f"\n✅ 已获取 token (用户ID: {uid})")
    
    # 示例1: 获取最近24小时的历史轨迹点
    print("\n" + "=" * 60)
    print("示例 1: 获取最近24小时的历史轨迹点")
    print("=" * 60)
    
    device_sn = input("请输入设备序列号 (sn): ").strip()
    if not device_sn:
        print("设备序列号不能为空")
        return
    
    # 计算时间范围（最近24小时）
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - 24 * 60 * 60 * 1000  # 24小时前
    
    result = get_history_track_points(
        token=token,
        uid=uid,
        sn=device_sn,
        start_time=start_time,
        end_time=end_time
    )
    
    # 示例2: 获取指定日期范围的历史轨迹点
    print("\n" + "=" * 60)
    print("示例 2: 获取指定日期范围的历史轨迹点")
    print("=" * 60)
    
    date_range_choice = input("是否获取指定日期范围的历史轨迹点? (y/n): ").strip().lower()
    
    if date_range_choice == 'y':
        try:
            start_date_str = input("请输入开始日期 (格式: YYYY-MM-DD，例如: 2024-01-01): ").strip()
            end_date_str = input("请输入结束日期 (格式: YYYY-MM-DD，例如: 2024-01-02): ").strip()
            
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            
            # 开始时间设为当天的 00:00:00
            start_time = int(start_date.timestamp() * 1000)
            # 结束时间设为当天的 23:59:59
            end_time = int((end_date + timedelta(days=1)).timestamp() * 1000) - 1
            
            result = get_history_track_points(
                token=token,
                uid=uid,
                sn=device_sn,
                start_time=start_time,
                end_time=end_time
            )
        except ValueError as e:
            print(f"日期格式错误: {e}")
        except Exception as e:
            print(f"错误: {e}")
    
    # 示例3: 导出历史轨迹点为 JSON
    if result and isinstance(result, list) and len(result) > 0:
        device_info = result[0]
        history_list = device_info.get('historyList', [])
        
        if history_list:
            export_choice = input("\n是否导出历史轨迹点为 JSON 文件? (y/n): ").strip().lower()
            if export_choice == 'y':
                filename = f"history_track_{device_sn}_{int(datetime.now().timestamp())}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump({
                        'device_sn': device_sn,
                        'start_time': start_time,
                        'end_time': end_time,
                        'point_count': len(history_list),
                        'history_points': history_list
                    }, f, indent=2, ensure_ascii=False)
                print(f"✅ 历史轨迹点已导出到: {filename}")


if __name__ == "__main__":
    main()
