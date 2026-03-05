#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单独解密一个加密的响应内容
"""

import json
import sys
import os

# 导入 query_tracks.py 中的解密函数
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from query_tracks import decrypt_api_response


if __name__ == "__main__":
    # 从用户提供的加密内容
    encrypted_content = {
        "encryption": "D/qRgdUGUz/k4ByjJndmlV0KLW4+JyqFB/9EFeAY7kEhqCeBFSkhKzvlqTFHZkvvyPqUlxCaIE/qj5pIuFsXZa9hORFkrHEEqwmVYXjiH5LQIdpsa4Xgvur0vYFFaznXe/psS/UvRkY="
    }
    
    # 从 token 文件读取 token
    try:
        with open('.citytag_token.json', 'r', encoding='utf-8') as f:
            token_data = json.load(f)
            token = token_data.get('token')
            uid = token_data.get('uid')
            username = token_data.get('username')
            print(f"使用 token: {token}")
            print(f"用户 ID: {uid}")
            print(f"用户名: {username}")
    except FileNotFoundError:
        print("错误: 找不到 .citytag_token.json 文件")
        print("请提供 token:")
        token = input("Token: ").strip()
    
    print("\n" + "=" * 60)
    print("解密请求参数")
    print("=" * 60)
    print(f"加密内容: {encrypted_content['encryption']}")
    
    try:
        # 解密
        decrypted_data = decrypt_api_response(token, encrypted_content['encryption'])
        
        print("\n" + "=" * 60)
        print("✅ 解密成功！解密后的查询参数:")
        print("=" * 60)
        print(json.dumps(decrypted_data, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n❌ 解密失败: {e}")
        import traceback
        traceback.print_exc()
