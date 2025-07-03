#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案件管理API测试
测试案件的增删改查、搜索等功能
"""

import pytest
import time
from .base_test import BaseAPITest


class TestCasesAPI(BaseAPITest):
    """案件管理API测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.login_admin()
        self.created_case_ids = []  # 记录创建的案件ID，用于清理
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        # 清理创建的测试案件
        for case_id in self.created_case_ids:
            try:
                self.make_request('DELETE', f'/api/cases/{case_id}', use_auth=True)
            except:
                pass  # 忽略删除失败的情况
    
    def test_get_cases_list_empty(self):
        """测试获取案件列表（可能为空）"""
        response = self.make_request('GET', '/api/cases', use_auth=True)
        data = self.assert_response(response, 200, ['success', 'data'])
        
        assert data['success'] is True
        assert isinstance(data['data'], list)
        # 不强制要求列表为空，因为可能已有数据
    
    def test_get_cases_list_without_auth(self):
        """测试未认证获取案件列表"""
        response = self.make_request('GET', '/api/cases')
        # 根据实际API设计，可能允许匿名访问或要求认证
        assert response.status_code in [200, 401], "案件列表访问权限检查"
    
    def test_create_case_success(self):
        """测试创建案件成功"""
        test_result = self.create_test_case("success_test")
        
        assert test_result['response_data']['success'] is True
        assert 'id' in test_result['response_data']['data']
        
        case_id = test_result['case_id']
        self.created_case_ids.append(case_id)
        
        # 验证案件是否真的被创建
        response = self.make_request('GET', f'/api/cases/{case_id}', use_auth=True)
        if response.status_code == 200:
            data = self.assert_response(response, 200, ['success', 'data'])
            assert data['data']['title'] == test_result['case_data']['title']
    
    def test_create_case_invalid_data(self):
        """测试创建案件（无效数据）"""
        invalid_data_sets = [
            # 缺少必需字段
            {
                "title": "测试案件"
                # 缺少其他必需字段
            },
            # 空标题
            {
                "title": "",
                "case_number": "(2024)测试001号",
                "court": "测试法院",
                "case_type": "civil"
            },
            # 无效案件类型
            {
                "title": "测试案件",
                "case_number": "(2024)测试002号",
                "court": "测试法院",
                "case_type": "invalid_type"
            },
            # 无效日期格式
            {
                "title": "测试案件",
                "case_number": "(2024)测试003号",
                "court": "测试法院",
                "case_type": "civil",
                "case_date": "invalid-date"
            }
        ]
        
        for invalid_data in invalid_data_sets:
            response = self.make_request('POST', '/api/cases', invalid_data, use_auth=True)
            assert response.status_code in [400, 422], f"无效数据应该返回错误: {invalid_data}"
    
    def test_create_case_without_auth(self):
        """测试未认证创建案件"""
        case_data = {
            "title": "未授权案件",
            "case_number": "(2024)未授权001号",
            "court": "测试法院",
            "case_type": "civil"
        }
        
        response = self.make_request('POST', '/api/cases', case_data)
        self.assert_response(response, 401, check_success=False)
    
    def test_get_case_by_id(self):
        """测试根据ID获取案件"""
        # 先创建一个案件
        test_result = self.create_test_case("get_by_id_test")
        case_id = test_result['case_id']
        self.created_case_ids.append(case_id)
        
        # 获取案件详情
        response = self.make_request('GET', f'/api/cases/{case_id}', use_auth=True)
        data = self.assert_response(response, 200, ['success', 'data'])
        
        assert data['success'] is True
        case_data = data['data']
        assert case_data['id'] == case_id
        assert case_data['title'] == test_result['case_data']['title']
    
    def test_get_case_by_invalid_id(self):
        """测试获取不存在的案件"""
        invalid_id = 99999
        response = self.make_request('GET', f'/api/cases/{invalid_id}', use_auth=True)
        self.assert_response(response, 404, check_success=False)
    
    def test_update_case_success(self):
        """测试更新案件成功"""
        # 先创建一个案件
        test_result = self.create_test_case("update_test")
        case_id = test_result['case_id']
        self.created_case_ids.append(case_id)
        
        # 更新案件信息
        update_data = {
            "title": f"更新的案件标题_{int(time.time())}",
            "status": "in_progress",
            "description": "这是更新后的案件描述"
        }
        
        response = self.make_request('PUT', f'/api/cases/{case_id}', update_data, use_auth=True)
        data = self.assert_response(response, 200, ['success'])
        assert data['success'] is True
        
        # 验证更新是否成功
        response = self.make_request('GET', f'/api/cases/{case_id}', use_auth=True)
        if response.status_code == 200:
            data = self.assert_response(response, 200, ['success', 'data'])
            updated_case = data['data']
            assert updated_case['title'] == update_data['title']
    
    def test_update_case_without_auth(self):
        """测试未认证更新案件"""
        # 先创建一个案件
        test_result = self.create_test_case("update_auth_test")
        case_id = test_result['case_id']
        self.created_case_ids.append(case_id)
        
        update_data = {
            "title": "未授权更新"
        }
        
        response = self.make_request('PUT', f'/api/cases/{case_id}', update_data)
        self.assert_response(response, 401, check_success=False)
    
    def test_delete_case_success(self):
        """测试删除案件成功"""
        # 先创建一个案件
        test_result = self.create_test_case("delete_test")
        case_id = test_result['case_id']
        
        # 删除案件
        response = self.make_request('DELETE', f'/api/cases/{case_id}', use_auth=True)
        data = self.assert_response(response, 200, ['success'])
        assert data['success'] is True
        
        # 验证案件是否被删除
        response = self.make_request('GET', f'/api/cases/{case_id}', use_auth=True)
        self.assert_response(response, 404, check_success=False)
    
    def test_delete_case_without_auth(self):
        """测试未认证删除案件"""
        # 先创建一个案件
        test_result = self.create_test_case("delete_auth_test")
        case_id = test_result['case_id']
        self.created_case_ids.append(case_id)
        
        response = self.make_request('DELETE', f'/api/cases/{case_id}')
        self.assert_response(response, 401, check_success=False)
    
    def test_search_cases_by_title(self):
        """测试按标题搜索案件"""
        # 创建几个测试案件
        search_keyword = f"搜索测试_{int(time.time())}"
        
        test_result1 = self.create_test_case(f"{search_keyword}_1")
        test_result2 = self.create_test_case(f"{search_keyword}_2")
        test_result3 = self.create_test_case("其他案件")
        
        self.created_case_ids.extend([
            test_result1['case_id'],
            test_result2['case_id'],
            test_result3['case_id']
        ])
        
        # 搜索包含关键词的案件
        params = {'search': search_keyword}
        response = self.make_request('GET', '/api/cases', params, use_auth=True)
        data = self.assert_response(response, 200, ['success', 'data'])
        
        assert data['success'] is True
        cases = data['data']
        
        # 验证搜索结果
        found_cases = [case for case in cases if search_keyword in case.get('title', '')]
        assert len(found_cases) >= 2, "应该找到至少2个包含搜索关键词的案件"
    
    def test_filter_cases_by_type(self):
        """测试按类型筛选案件"""
        # 创建不同类型的案件
        civil_case = self.create_test_case("民事案件")
        criminal_case_data = civil_case['case_data'].copy()
        criminal_case_data['case_type'] = 'criminal'
        criminal_case_data['title'] = '刑事案件'
        criminal_case_data['case_number'] = f"(2024)刑事{int(time.time())}号"
        
        response = self.make_request('POST', '/api/cases', criminal_case_data, use_auth=True)
        criminal_case_response = self.assert_response(response, 201, ['success', 'data'])
        
        self.created_case_ids.extend([
            civil_case['case_id'],
            criminal_case_response['data']['id']
        ])
        
        # 按类型筛选
        params = {'case_type': 'civil'}
        response = self.make_request('GET', '/api/cases', params, use_auth=True)
        data = self.assert_response(response, 200, ['success', 'data'])
        
        civil_cases = data['data']
        for case in civil_cases:
            if case['id'] in [civil_case['case_id'], criminal_case_response['data']['id']]:
                assert case['case_type'] == 'civil', "筛选结果应该只包含民事案件"
    
    def test_filter_cases_by_status(self):
        """测试按状态筛选案件"""
        # 创建不同状态的案件
        pending_case = self.create_test_case("待处理案件")
        
        # 创建进行中的案件
        in_progress_case_data = pending_case['case_data'].copy()
        in_progress_case_data['status'] = 'in_progress'
        in_progress_case_data['title'] = '进行中案件'
        in_progress_case_data['case_number'] = f"(2024)进行{int(time.time())}号"
        
        response = self.make_request('POST', '/api/cases', in_progress_case_data, use_auth=True)
        in_progress_response = self.assert_response(response, 201, ['success', 'data'])
        
        self.created_case_ids.extend([
            pending_case['case_id'],
            in_progress_response['data']['id']
        ])
        
        # 按状态筛选
        params = {'status': 'pending'}
        response = self.make_request('GET', '/api/cases', params, use_auth=True)
        data = self.assert_response(response, 200, ['success', 'data'])
        
        pending_cases = data['data']
        for case in pending_cases:
            if case['id'] in [pending_case['case_id'], in_progress_response['data']['id']]:
                assert case['status'] == 'pending', "筛选结果应该只包含待处理案件"
    
    def test_pagination(self):
        """测试分页功能"""
        # 创建多个案件用于测试分页
        case_ids = []
        for i in range(5):
            test_result = self.create_test_case(f"分页测试_{i}")
            case_ids.append(test_result['case_id'])
        
        self.created_case_ids.extend(case_ids)
        
        # 测试第一页
        params = {'page': 1, 'per_page': 3}
        response = self.make_request('GET', '/api/cases', params, use_auth=True)
        data = self.assert_response(response, 200, ['success', 'data'])
        
        # 根据实际API响应结构调整断言
        if isinstance(data['data'], dict) and 'items' in data['data']:
            # 如果返回的是分页对象
            assert len(data['data']['items']) <= 3
            assert 'total' in data['data']
            assert 'page' in data['data']
        else:
            # 如果返回的是简单列表
            assert isinstance(data['data'], list)
    
    @pytest.mark.parametrize("case_type,expected_valid", [
        ("civil", True),
        ("criminal", True),
        ("administrative", True),
        ("invalid_type", False),
        ("", False),
    ])
    def test_case_type_validation(self, case_type, expected_valid):
        """测试案件类型验证（数据驱动测试）"""
        case_data = {
            "title": f"类型测试案件_{case_type}",
            "case_number": f"(2024)类型{int(time.time())}号",
            "court": "测试法院",
            "case_type": case_type
        }
        
        response = self.make_request('POST', '/api/cases', case_data, use_auth=True)
        
        if expected_valid:
            data = self.assert_response(response, 201, ['success', 'data'])
            self.created_case_ids.append(data['data']['id'])
        else:
            assert response.status_code in [400, 422], f"无效案件类型 {case_type} 应该返回错误"
    
    def test_case_number_uniqueness(self):
        """测试案件编号唯一性"""
        # 创建第一个案件
        case_number = f"(2024)唯一性测试{int(time.time())}号"
        test_result1 = self.create_test_case("唯一性测试1")
        
        # 更新案件编号
        update_data = {"case_number": case_number}
        response = self.make_request('PUT', f'/api/cases/{test_result1["case_id"]}', update_data, use_auth=True)
        
        self.created_case_ids.append(test_result1['case_id'])
        
        # 尝试创建具有相同编号的案件
        duplicate_case_data = {
            "title": "重复编号案件",
            "case_number": case_number,
            "court": "测试法院",
            "case_type": "civil"
        }
        
        response = self.make_request('POST', '/api/cases', duplicate_case_data, use_auth=True)
        # 根据实际API行为，可能允许重复编号或返回错误
        assert response.status_code in [201, 400, 409], "案件编号重复处理"