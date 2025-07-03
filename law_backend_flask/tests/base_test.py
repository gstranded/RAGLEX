#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接口测试基类
提供统一的API测试基础功能
"""

import pytest
import requests
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime


class BaseAPITest:
    """API测试基类"""
    
    BASE_URL = 'http://localhost:5000'
    HEADERS = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    def __init__(self):
        self.auth_token = None
        self.auth_headers = self.HEADERS.copy()
        self.test_user_id = None
    
    def make_request(self, method: str, endpoint: str, 
                    data: Optional[Dict] = None, 
                    headers: Optional[Dict] = None,
                    use_auth: bool = False,
                    files: Optional[Dict] = None) -> requests.Response:
        """统一的请求方法"""
        url = f"{self.BASE_URL}{endpoint}"
        request_headers = headers or (self.auth_headers if use_auth else self.HEADERS)
        
        # 如果有文件上传，移除Content-Type让requests自动设置
        if files and 'Content-Type' in request_headers:
            request_headers = request_headers.copy()
            del request_headers['Content-Type']
        
        try:
            if method.upper() == 'GET':
                return requests.get(url, headers=request_headers, params=data, timeout=30)
            elif method.upper() == 'POST':
                if files:
                    return requests.post(url, headers=request_headers, data=data, files=files, timeout=30)
                else:
                    return requests.post(url, headers=request_headers, json=data, timeout=30)
            elif method.upper() == 'PUT':
                return requests.put(url, headers=request_headers, json=data, timeout=30)
            elif method.upper() == 'DELETE':
                return requests.delete(url, headers=request_headers, timeout=30)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"请求失败: {e}")
    
    def assert_response(self, response: requests.Response, 
                       expected_status: int = 200,
                       expected_keys: List[str] = None,
                       check_success: bool = True) -> Dict[str, Any]:
        """响应断言"""
        assert response.status_code == expected_status, \
            f"期望状态码 {expected_status}，实际 {response.status_code}。响应内容: {response.text}"
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            if expected_status >= 400:
                # 错误响应可能不是JSON格式
                return {"error": response.text}
            pytest.fail(f"响应不是有效的JSON: {response.text}")
        
        if expected_keys:
            for key in expected_keys:
                assert key in data, f"响应中缺少必需的键: {key}。实际响应: {data}"
        
        if check_success and expected_status < 400:
            assert data.get('success') is True, f"API调用失败: {data.get('message', '未知错误')}"
        
        return data
    
    def login_admin(self) -> str:
        """管理员登录并返回token"""
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = self.make_request('POST', '/api/auth/login', login_data)
        data = self.assert_response(response, 200, ['success', 'data'])
        
        if data.get('success') and 'access_token' in data.get('data', {}):
            self.auth_token = data['data']['access_token']
            self.auth_headers['Authorization'] = f'Bearer {self.auth_token}'
            self.test_user_id = data['data'].get('user', {}).get('id')
            return self.auth_token
        
        pytest.fail(f"登录失败: {data}")
    
    def create_test_user(self, username_suffix: str = None) -> Dict[str, Any]:
        """创建测试用户"""
        timestamp = int(time.time())
        suffix = username_suffix or str(timestamp)
        
        user_data = {
            "username": f"testuser_{suffix}",
            "email": f"test_{suffix}@example.com",
            "password": "testpass123",
            "full_name": f"测试用户_{suffix}"
        }
        
        response = self.make_request('POST', '/api/auth/register', user_data)
        data = self.assert_response(response, 201, ['success', 'data'])
        
        return {
            'user_data': user_data,
            'response_data': data
        }
    
    def create_test_case(self, title_suffix: str = None) -> Dict[str, Any]:
        """创建测试案件（需要先登录）"""
        if not self.auth_token:
            self.login_admin()
        
        timestamp = int(time.time())
        suffix = title_suffix or str(timestamp)
        
        case_data = {
            "title": f"测试案件_{suffix}",
            "case_number": f"(2024)测试{suffix}号",
            "court": "测试法院",
            "case_type": "civil",
            "status": "pending",
            "plaintiff": "测试原告",
            "defendant": "测试被告",
            "case_date": "2024-01-01",
            "description": f"这是一个测试案件_{suffix}"
        }
        
        response = self.make_request('POST', '/api/cases', case_data, use_auth=True)
        data = self.assert_response(response, 201, ['success', 'data'])
        
        return {
            'case_data': case_data,
            'case_id': data['data']['id'],
            'response_data': data
        }
    
    def create_test_conversation(self, title_suffix: str = None) -> Dict[str, Any]:
        """创建测试对话（需要先登录）"""
        if not self.auth_token:
            self.login_admin()
        
        timestamp = int(time.time())
        suffix = title_suffix or str(timestamp)
        
        conversation_data = {
            "title": f"测试对话_{suffix}"
        }
        
        response = self.make_request('POST', '/api/conversations', conversation_data, use_auth=True)
        data = self.assert_response(response, 201, ['success', 'data'])
        
        return {
            'conversation_data': conversation_data,
            'conversation_id': data['data']['id'],
            'response_data': data
        }
    
    def wait_for_server(self, max_attempts: int = 30, delay: float = 1.0) -> bool:
        """等待服务器启动"""
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            
            if attempt < max_attempts - 1:
                time.sleep(delay)
        
        return False
    
    def print_response_debug(self, response: requests.Response, test_name: str):
        """打印响应调试信息"""
        print(f"\n{'='*50}")
        print(f"测试: {test_name}")
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        try:
            print(f"响应体: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except:
            print(f"响应体: {response.text}")
        print(f"{'='*50}")
    
    def cleanup_test_data(self):
        """清理测试数据（可在子类中重写）"""
        pass
    
    def setup_method(self):
        """每个测试方法前的设置"""
        pass
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        self.cleanup_test_data()