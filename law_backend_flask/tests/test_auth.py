#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证API测试
测试用户注册、登录、个人信息管理等功能
"""

import pytest
import time
from .base_test import BaseAPITest


class TestAuthAPI(BaseAPITest):
    """认证API测试类"""
    
    def test_health_check(self):
        """测试健康检查"""
        response = self.make_request('GET', '/health')
        data = self.assert_response(response, 200)
        assert 'status' in data or 'message' in data
    
    def test_user_registration_success(self):
        """测试用户注册成功"""
        test_result = self.create_test_user()
        assert test_result['response_data']['success'] is True
        assert 'message' in test_result['response_data']
    
    def test_user_registration_duplicate_username(self):
        """测试重复用户名注册"""
        # 先创建一个用户
        test_result = self.create_test_user("duplicate_test")
        
        # 尝试用相同用户名再次注册
        user_data = {
            "username": test_result['user_data']['username'],
            "email": "different@example.com",
            "password": "testpass123",
            "full_name": "不同的用户"
        }
        
        response = self.make_request('POST', '/api/auth/register', user_data)
        self.assert_response(response, 400, check_success=False)
    
    def test_user_registration_duplicate_email(self):
        """测试重复邮箱注册"""
        # 先创建一个用户
        test_result = self.create_test_user("email_test")
        
        # 尝试用相同邮箱再次注册
        user_data = {
            "username": "different_user",
            "email": test_result['user_data']['email'],
            "password": "testpass123",
            "full_name": "不同的用户"
        }
        
        response = self.make_request('POST', '/api/auth/register', user_data)
        self.assert_response(response, 400, check_success=False)
    
    def test_user_registration_invalid_data(self):
        """测试无效数据注册"""
        invalid_data_sets = [
            # 缺少必需字段
            {
                "username": "testuser",
                "password": "testpass123"
                # 缺少email和full_name
            },
            # 空用户名
            {
                "username": "",
                "email": "test@example.com",
                "password": "testpass123",
                "full_name": "测试用户"
            },
            # 无效邮箱格式
            {
                "username": "testuser",
                "email": "invalid-email",
                "password": "testpass123",
                "full_name": "测试用户"
            },
            # 密码太短
            {
                "username": "testuser",
                "email": "test@example.com",
                "password": "123",
                "full_name": "测试用户"
            }
        ]
        
        for invalid_data in invalid_data_sets:
            response = self.make_request('POST', '/api/auth/register', invalid_data)
            assert response.status_code == 400, f"无效数据应该返回400错误: {invalid_data}"
    
    def test_user_login_success(self):
        """测试用户登录成功"""
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = self.make_request('POST', '/api/auth/login', login_data)
        data = self.assert_response(response, 200, ['success', 'data'])
        
        assert data['success'] is True
        assert 'access_token' in data['data']
        assert 'user' in data['data']
        assert data['data']['user']['username'] == 'admin'
    
    def test_user_login_invalid_username(self):
        """测试无效用户名登录"""
        login_data = {
            "username": "nonexistent_user",
            "password": "admin123"
        }
        
        response = self.make_request('POST', '/api/auth/login', login_data)
        self.assert_response(response, 401, check_success=False)
    
    def test_user_login_invalid_password(self):
        """测试无效密码登录"""
        login_data = {
            "username": "admin",
            "password": "wrongpassword"
        }
        
        response = self.make_request('POST', '/api/auth/login', login_data)
        self.assert_response(response, 401, check_success=False)
    
    def test_user_login_empty_credentials(self):
        """测试空凭据登录"""
        login_data = {
            "username": "",
            "password": ""
        }
        
        response = self.make_request('POST', '/api/auth/login', login_data)
        self.assert_response(response, 400, check_success=False)
    
    def test_get_profile_with_auth(self):
        """测试获取用户资料（需要认证）"""
        self.login_admin()
        
        response = self.make_request('GET', '/api/auth/profile', use_auth=True)
        data = self.assert_response(response, 200, ['success', 'data'])
        
        assert data['success'] is True
        user_data = data['data']
        assert 'username' in user_data
        assert 'email' in user_data
        assert 'id' in user_data
        assert user_data['username'] == 'admin'
    
    def test_get_profile_without_auth(self):
        """测试未认证获取用户资料"""
        response = self.make_request('GET', '/api/auth/profile')
        self.assert_response(response, 401, check_success=False)
    
    def test_get_profile_invalid_token(self):
        """测试无效token获取用户资料"""
        invalid_headers = self.HEADERS.copy()
        invalid_headers['Authorization'] = 'Bearer invalid_token_here'
        
        response = self.make_request('GET', '/api/auth/profile', headers=invalid_headers)
        self.assert_response(response, 401, check_success=False)
    
    def test_update_profile_success(self):
        """测试更新用户资料成功"""
        self.login_admin()
        
        # 先获取当前资料
        response = self.make_request('GET', '/api/auth/profile', use_auth=True)
        original_data = self.assert_response(response, 200, ['success', 'data'])
        
        # 更新资料
        update_data = {
            "full_name": f"更新的管理员_{int(time.time())}",
            "phone": "13800138000",
            "bio": "这是更新后的个人简介"
        }
        
        response = self.make_request('PUT', '/api/auth/profile', update_data, use_auth=True)
        data = self.assert_response(response, 200, ['success'])
        assert data['success'] is True
        
        # 验证更新是否成功
        response = self.make_request('GET', '/api/auth/profile', use_auth=True)
        updated_data = self.assert_response(response, 200, ['success', 'data'])
        
        if 'full_name' in updated_data['data']:
            assert updated_data['data']['full_name'] == update_data['full_name']
    
    def test_update_profile_without_auth(self):
        """测试未认证更新用户资料"""
        update_data = {
            "full_name": "未授权更新"
        }
        
        response = self.make_request('PUT', '/api/auth/profile', update_data)
        self.assert_response(response, 401, check_success=False)
    
    def test_update_profile_invalid_data(self):
        """测试无效数据更新用户资料"""
        self.login_admin()
        
        # 尝试更新为无效邮箱格式
        update_data = {
            "email": "invalid-email-format"
        }
        
        response = self.make_request('PUT', '/api/auth/profile', update_data, use_auth=True)
        # 根据实际API行为调整期望状态码
        assert response.status_code in [400, 422], "无效邮箱格式应该返回错误"
    
    @pytest.mark.parametrize("username,password,expected_status", [
        ("admin", "admin123", 200),  # 正确凭据
        ("admin", "wrongpass", 401),  # 错误密码
        ("nonexistent", "password", 401),  # 不存在的用户
        ("", "", 400),  # 空凭据
        ("admin", "", 400),  # 空密码
        ("", "admin123", 400),  # 空用户名
    ])
    def test_login_scenarios(self, username, password, expected_status):
        """测试多种登录场景（数据驱动测试）"""
        login_data = {
            "username": username,
            "password": password
        }
        
        response = self.make_request('POST', '/api/auth/login', login_data)
        assert response.status_code == expected_status, \
            f"用户名: {username}, 密码: {password}, 期望: {expected_status}, 实际: {response.status_code}"
    
    def test_token_expiration_simulation(self):
        """测试token过期模拟（如果API支持）"""
        # 这个测试需要根据实际的token过期机制来实现
        # 目前只是一个占位符，展示如何测试token过期
        self.login_admin()
        
        # 正常请求应该成功
        response = self.make_request('GET', '/api/auth/profile', use_auth=True)
        self.assert_response(response, 200)
        
        # 如果有token刷新机制，可以在这里测试
        # 如果有token过期时间设置，可以等待过期后测试
    
    def test_concurrent_login_sessions(self):
        """测试并发登录会话"""
        # 第一次登录
        token1 = self.login_admin()
        
        # 第二次登录（模拟不同设备）
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        response = self.make_request('POST', '/api/auth/login', login_data)
        data = self.assert_response(response, 200, ['success', 'data'])
        token2 = data['data']['access_token']
        
        # 验证两个token都有效（如果API支持多会话）
        headers1 = self.HEADERS.copy()
        headers1['Authorization'] = f'Bearer {token1}'
        
        headers2 = self.HEADERS.copy()
        headers2['Authorization'] = f'Bearer {token2}'
        
        response1 = self.make_request('GET', '/api/auth/profile', headers=headers1)
        response2 = self.make_request('GET', '/api/auth/profile', headers=headers2)
        
        # 根据实际API行为调整断言
        assert response1.status_code in [200, 401], "第一个token状态"
        assert response2.status_code == 200, "第二个token应该有效"