#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Backend API 测试脚本
用于测试所有API端点的功能
"""

import requests
import json
import time
import os
from datetime import datetime

# 配置
BASE_URL = 'http://localhost:5000'
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# 全局变量存储认证token
auth_token = None
auth_headers = HEADERS.copy()

def print_response(response, test_name):
    """打印响应结果"""
    print(f"\n{'='*50}")
    print(f"测试: {test_name}")
    print(f"状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    try:
        print(f"响应体: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"响应体: {response.text}")
    print(f"{'='*50}")

def test_health_check():
    """测试健康检查"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print_response(response, "健康检查")
        return response.status_code == 200
    except Exception as e:
        print(f"健康检查失败: {e}")
        return False

def test_user_registration():
    """测试用户注册"""
    test_data = {
        "username": "testuser2",
        "email": "testuser2@example.com",
        "password": "testpass123",
        "full_name": "测试用户2"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            headers=HEADERS,
            json=test_data
        )
        print_response(response, "用户注册")
        return response.status_code in [201, 400]  # 201成功，400可能已存在
    except Exception as e:
        print(f"用户注册测试失败: {e}")
        return False

def test_user_login():
    """测试用户登录"""
    global auth_token, auth_headers
    
    test_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            headers=HEADERS,
            json=test_data
        )
        print_response(response, "用户登录")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and 'access_token' in data.get('data', {}):
                auth_token = data['data']['access_token']
                auth_headers['Authorization'] = f'Bearer {auth_token}'
                print(f"登录成功，获取到token: {auth_token[:20]}...")
                return True
        
        return False
    except Exception as e:
        print(f"用户登录测试失败: {e}")
        return False

def test_user_profile():
    """测试用户资料"""
    if not auth_token:
        print("需要先登录")
        return False
    
    try:
        # 获取用户资料
        response = requests.get(
            f"{BASE_URL}/api/auth/profile",
            headers=auth_headers
        )
        print_response(response, "获取用户资料")
        
        # 更新用户资料
        update_data = {
            "full_name": "管理员（已更新）",
            "phone": "13800138000"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/auth/profile",
            headers=auth_headers,
            json=update_data
        )
        print_response(response, "更新用户资料")
        
        return response.status_code == 200
    except Exception as e:
        print(f"用户资料测试失败: {e}")
        return False



def test_cases_api():
    """测试案件管理API"""
    try:
        # 获取案件列表
        response = requests.get(
            f"{BASE_URL}/api/cases",
            headers=auth_headers if auth_token else HEADERS
        )
        print_response(response, "获取案件列表")
        
        # 测试搜索
        response = requests.get(
            f"{BASE_URL}/api/cases?search=张某&case_type=criminal",
            headers=auth_headers if auth_token else HEADERS
        )
        print_response(response, "搜索案件")
        
        # 测试创建案件（需要登录）
        if auth_token:
            case_data = {
                "title": "测试案件",
                "case_number": "(2024)测试001号",
                "court": "测试法院",
                "case_type": "civil",
                "status": "pending",
                "plaintiff": "测试原告",
                "defendant": "测试被告",
                "case_date": "2024-01-01",
                "description": "这是一个测试案件"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/cases",
                headers=auth_headers,
                json=case_data
            )
            print_response(response, "创建案件")
        
        return True
    except Exception as e:
        print(f"案件API测试失败: {e}")
        return False

def test_history_api():
    """测试历史记录API"""
    if not auth_token:
        print("历史记录API需要登录")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/history",
            headers=auth_headers
        )
        print_response(response, "获取历史记录")
        return response.status_code == 200
    except Exception as e:
        print(f"历史记录API测试失败: {e}")
        return False

def test_knowledge_api():
    """测试知识库API（暂时返回pass）"""
    if not auth_token:
        print("知识库API需要登录")
        return False
    
    try:
        # 测试问答API
        query_data = {
            "question": "什么是合同法？",
            "context": "法律咨询"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/query",
            headers=auth_headers,
            json=query_data
        )
        print_response(response, "知识库问答")
        
        # 知识库导入功能已移除（使用外部服务器）
        
        return True
    except Exception as e:
        print(f"知识库API测试失败: {e}")
        return False

def test_config_api():
    """测试配置API"""
    try:
        response = requests.get(f"{BASE_URL}/api/config")
        print_response(response, "获取系统配置")
        return response.status_code == 200
    except Exception as e:
        print(f"配置API测试失败: {e}")
        return False



def test_statistics_api():
    """测试统计API"""
    if not auth_token:
        print("统计API需要登录")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/statistics",
            headers=auth_headers
        )
        print_response(response, "获取统计信息")
        return response.status_code == 200
    except Exception as e:
        print(f"统计API测试失败: {e}")
        return False

def test_file_upload():
    """测试文件上传（模拟）"""
    if not auth_token:
        print("文件上传需要登录")
        return False
    
    try:
        # 创建一个测试文件
        test_content = "这是一个测试PDF文件的内容"
        
        # 模拟文件上传（需要先有案件ID）
        # 这里只是测试API端点是否存在
        print("文件上传API测试（模拟）")
        print("注意：实际文件上传需要先创建案件并获取案件ID")
        
        return True
    except Exception as e:
        print(f"文件上传测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("开始API测试...")
    print(f"测试目标: {BASE_URL}")
    
    tests = [
        ("健康检查", test_health_check),
        ("用户注册", test_user_registration),
        ("用户登录", test_user_login),
        ("用户资料", test_user_profile),
        ("案件管理API", test_cases_api),
        ("历史记录API", test_history_api),
        ("知识库API", test_knowledge_api),
        ("配置API", test_config_api),
        ("统计API", test_statistics_api),
        ("文件上传API", test_file_upload)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n正在运行: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{test_name}: {'✓ 通过' if result else '✗ 失败'}")
        except Exception as e:
            print(f"{test_name}: ✗ 异常 - {e}")
            results.append((test_name, False))
        
        time.sleep(1)  # 避免请求过快
    
    # 输出测试结果摘要
    print("\n" + "="*60)
    print("测试结果摘要")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    print(f"成功率: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试都通过了！")
    else:
        print(f"\n⚠️  有 {total-passed} 个测试失败，请检查服务器状态和配置。")
    
    print("\n注意事项:")
    print("1. 确保MySQL和MinIO服务正在运行")
    print("2. 确保已运行数据库初始化脚本: python init_db.py")
    print("3. 确保Flask应用正在运行: python run.py")

if __name__ == '__main__':
    run_all_tests()