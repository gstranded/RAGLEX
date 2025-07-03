#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例测试文件
展示如何使用RAGLEX API测试框架
"""

import pytest
import time
from .base_test import BaseAPITest


class TestExampleAPI(BaseAPITest):
    """示例API测试类
    
    这个类展示了如何使用测试框架编写API测试
    """
    
    def setup_method(self):
        """每个测试方法前的设置
        
        这里可以进行测试前的准备工作，如登录、创建测试数据等
        """
        # 登录管理员账户（如果测试需要认证）
        self.login_admin()
        
        # 初始化测试数据
        self.test_data = {
            'example_field': 'test_value',
            'timestamp': int(time.time())
        }
    
    def teardown_method(self):
        """每个测试方法后的清理
        
        这里可以进行测试后的清理工作，如删除测试数据等
        """
        # 清理测试数据的代码
        pass
    
    @pytest.mark.smoke
    def test_health_check(self):
        """测试健康检查API
        
        这是一个基础的冒烟测试，验证服务是否正常运行
        """
        response = self.make_request('GET', '/api/health')
        
        # 验证响应状态码
        assert response.status_code == 200
        
        # 验证响应内容
        data = response.json()
        assert 'status' in data
        assert data['status'] == 'healthy'
    
    @pytest.mark.api
    def test_get_request_example(self):
        """GET请求示例
        
        展示如何测试GET请求
        """
        # 发送GET请求
        response = self.make_request('GET', '/api/cases', use_auth=True)
        
        # 使用基类的断言方法验证响应
        data = self.assert_response(response, 200, ['success', 'data'])
        
        # 验证响应数据结构
        assert data['success'] is True
        assert isinstance(data['data'], list)
    
    @pytest.mark.api
    def test_post_request_example(self):
        """POST请求示例
        
        展示如何测试POST请求
        """
        # 准备请求数据
        case_data = {
            'case_number': f'EXAMPLE-{int(time.time())}',
            'case_title': '示例案件标题',
            'case_type': '合同纠纷',
            'case_description': '这是一个示例案件描述'
        }
        
        # 发送POST请求
        response = self.make_request('POST', '/api/cases', case_data, use_auth=True)
        
        # 验证响应
        if response.status_code == 201:
            data = self.assert_response(response, 201, ['success', 'data'])
            assert data['success'] is True
            
            # 验证返回的案件数据
            case_info = data['data']
            assert case_info['case_title'] == case_data['case_title']
            assert case_info['case_type'] == case_data['case_type']
            
            # 记录创建的案件ID，用于后续清理
            self.created_case_id = case_info.get('id')
        else:
            # 如果API不支持或返回其他状态码
            assert response.status_code in [400, 404, 501], "案件创建API状态检查"
    
    @pytest.mark.api
    def test_put_request_example(self):
        """PUT请求示例
        
        展示如何测试PUT请求（更新操作）
        """
        # 首先创建一个案件
        case_data = {
            'case_number': f'UPDATE-{int(time.time())}',
            'case_title': '待更新的案件',
            'case_type': '民事纠纷'
        }
        
        create_response = self.make_request('POST', '/api/cases', case_data, use_auth=True)
        
        if create_response.status_code == 201:
            create_data = self.assert_response(create_response, 201, ['success', 'data'])
            case_id = create_data['data']['id']
            
            # 更新案件数据
            update_data = {
                'case_title': '已更新的案件标题',
                'case_description': '这是更新后的案件描述'
            }
            
            # 发送PUT请求
            response = self.make_request('PUT', f'/api/cases/{case_id}', update_data, use_auth=True)
            
            if response.status_code == 200:
                data = self.assert_response(response, 200, ['success'])
                assert data['success'] is True
            else:
                assert response.status_code in [404, 501], "案件更新API状态检查"
    
    @pytest.mark.api
    def test_delete_request_example(self):
        """DELETE请求示例
        
        展示如何测试DELETE请求
        """
        # 首先创建一个案件
        case_data = {
            'case_number': f'DELETE-{int(time.time())}',
            'case_title': '待删除的案件',
            'case_type': '刑事案件'
        }
        
        create_response = self.make_request('POST', '/api/cases', case_data, use_auth=True)
        
        if create_response.status_code == 201:
            create_data = self.assert_response(create_response, 201, ['success', 'data'])
            case_id = create_data['data']['id']
            
            # 发送DELETE请求
            response = self.make_request('DELETE', f'/api/cases/{case_id}', use_auth=True)
            
            if response.status_code == 200:
                data = self.assert_response(response, 200, ['success'])
                assert data['success'] is True
                
                # 验证案件是否被删除
                get_response = self.make_request('GET', f'/api/cases/{case_id}', use_auth=True)
                assert get_response.status_code == 404
            else:
                assert response.status_code in [404, 501], "案件删除API状态检查"
    
    @pytest.mark.api
    def test_error_handling_example(self):
        """错误处理示例
        
        展示如何测试错误场景
        """
        # 测试无效的案件ID
        invalid_id = 99999
        response = self.make_request('GET', f'/api/cases/{invalid_id}', use_auth=True)
        
        # 验证返回404错误
        self.assert_response(response, 404, check_success=False)
        
        # 测试无效的请求数据
        invalid_data = {
            'invalid_field': 'invalid_value'
        }
        
        response = self.make_request('POST', '/api/cases', invalid_data, use_auth=True)
        
        # 验证返回400或422错误
        assert response.status_code in [400, 422], "无效数据应该返回客户端错误"
    
    @pytest.mark.auth
    def test_authentication_example(self):
        """认证测试示例
        
        展示如何测试需要认证的API
        """
        # 测试未认证的请求
        response = self.make_request('GET', '/api/cases')
        
        # 验证返回401未授权错误
        self.assert_response(response, 401, check_success=False)
        
        # 测试已认证的请求
        response = self.make_request('GET', '/api/cases', use_auth=True)
        
        # 验证请求成功
        self.assert_response(response, 200, ['success', 'data'])
    
    @pytest.mark.parametrize("case_type,expected_status", [
        ('合同纠纷', 201),
        ('劳动争议', 201),
        ('知识产权', 201),
        ('无效类型', 400),
        ('', 400),
    ])
    def test_parametrized_example(self, case_type, expected_status):
        """参数化测试示例
        
        展示如何使用参数化测试多个场景
        """
        case_data = {
            'case_number': f'PARAM-{int(time.time())}-{case_type}',
            'case_title': f'参数化测试案件-{case_type}',
            'case_type': case_type
        }
        
        response = self.make_request('POST', '/api/cases', case_data, use_auth=True)
        
        # 根据预期状态码验证响应
        if expected_status == 201:
            if response.status_code == 201:
                data = self.assert_response(response, 201, ['success', 'data'])
                assert data['success'] is True
            else:
                # 如果API不支持，跳过测试
                pytest.skip("案件创建API不可用")
        else:
            assert response.status_code == expected_status or response.status_code in [404, 501]
    
    @pytest.mark.slow
    def test_performance_example(self):
        """性能测试示例
        
        展示如何测试API性能
        """
        # 记录开始时间
        start_time = time.time()
        
        # 发送请求
        response = self.make_request('GET', '/api/cases', use_auth=True)
        
        # 计算响应时间
        response_time = time.time() - start_time
        
        # 验证响应时间在可接受范围内
        assert response_time < 2.0, f"API响应时间过长: {response_time:.2f}秒"
        
        # 验证响应成功
        self.assert_response(response, 200, ['success', 'data'])
    
    @pytest.mark.integration
    def test_workflow_example(self):
        """工作流测试示例
        
        展示如何测试完整的业务流程
        """
        # 步骤1: 创建案件
        case_data = {
            'case_number': f'WORKFLOW-{int(time.time())}',
            'case_title': '工作流测试案件',
            'case_type': '商事纠纷',
            'case_description': '这是一个工作流测试案件'
        }
        
        create_response = self.make_request('POST', '/api/cases', case_data, use_auth=True)
        
        if create_response.status_code != 201:
            pytest.skip("案件创建API不可用，跳过工作流测试")
        
        create_data = self.assert_response(create_response, 201, ['success', 'data'])
        case_id = create_data['data']['id']
        
        # 步骤2: 查询案件
        get_response = self.make_request('GET', f'/api/cases/{case_id}', use_auth=True)
        get_data = self.assert_response(get_response, 200, ['success', 'data'])
        
        assert get_data['data']['case_title'] == case_data['case_title']
        
        # 步骤3: 更新案件
        update_data = {
            'case_description': '这是更新后的案件描述'
        }
        
        update_response = self.make_request('PUT', f'/api/cases/{case_id}', update_data, use_auth=True)
        
        if update_response.status_code == 200:
            self.assert_response(update_response, 200, ['success'])
        
        # 步骤4: 删除案件
        delete_response = self.make_request('DELETE', f'/api/cases/{case_id}', use_auth=True)
        
        if delete_response.status_code == 200:
            self.assert_response(delete_response, 200, ['success'])
            
            # 验证案件已被删除
            final_get_response = self.make_request('GET', f'/api/cases/{case_id}', use_auth=True)
            assert final_get_response.status_code == 404
    
    def test_custom_assertion_example(self):
        """自定义断言示例
        
        展示如何使用基类提供的断言方法
        """
        response = self.make_request('GET', '/api/health')
        
        # 使用基类的断言方法
        data = self.assert_response(response, 200, ['status'])
        
        # 自定义断言
        assert data['status'] == 'healthy', "服务状态应该是healthy"
        
        # 验证响应时间
        assert hasattr(response, 'elapsed'), "响应对象应该包含elapsed属性"
        
        # 验证响应头
        assert 'Content-Type' in response.headers, "响应应该包含Content-Type头"
    
    def test_debug_information_example(self):
        """调试信息示例
        
        展示如何在测试中输出调试信息
        """
        response = self.make_request('GET', '/api/health')
        
        # 使用基类的调试方法
        self.print_debug(f"响应状态码: {response.status_code}")
        self.print_debug(f"响应头: {dict(response.headers)}")
        self.print_debug(f"响应内容: {response.text}")
        
        # 验证响应
        self.assert_response(response, 200, ['status'])


# 独立的测试函数示例
@pytest.mark.unit
def test_independent_function_example():
    """独立测试函数示例
    
    展示如何编写不依赖类的测试函数
    """
    # 这种测试适合测试纯函数或工具方法
    from test_config import config
    
    # 测试配置
    assert config.BASE_URL is not None
    assert config.TIMEOUT > 0
    
    # 测试工具方法
    test_user_data = config.get_test_user_data('example')
    assert 'username' in test_user_data
    assert 'email' in test_user_data
    assert test_user_data['username'].startswith('test_user_')


@pytest.mark.skip(reason="这是一个跳过的测试示例")
def test_skipped_example():
    """跳过的测试示例
    
    展示如何跳过某些测试
    """
    # 这个测试会被跳过
    pass


@pytest.mark.xfail(reason="这是一个预期失败的测试示例")
def test_expected_failure_example():
    """预期失败的测试示例
    
    展示如何标记预期失败的测试
    """
    # 这个测试预期会失败
    assert False, "这是一个预期的失败"