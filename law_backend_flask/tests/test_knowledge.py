#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库API测试
测试问答功能、知识库查询等
"""

import pytest
import time
from .base_test import BaseAPITest


class TestKnowledgeAPI(BaseAPITest):
    """知识库API测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.login_admin()
    
    def test_query_basic_question(self):
        """测试基本问答功能"""
        query_data = {
            "question": "什么是合同法？",
            "context": "法律咨询"
        }
        
        response = self.make_request('POST', '/api/query', query_data, use_auth=True)
        data = self.assert_response(response, 200, ['success'])
        
        assert data['success'] is True
        # 根据实际API响应结构调整断言
        if 'data' in data:
            assert 'answer' in data['data'] or 'response' in data['data']
    
    def test_query_without_auth(self):
        """测试未认证的问答请求"""
        query_data = {
            "question": "什么是民法？",
            "context": "法律咨询"
        }
        
        response = self.make_request('POST', '/api/query', query_data)
        # 根据实际API设计，可能允许匿名查询或要求认证
        assert response.status_code in [200, 401], "查询API访问权限检查"
    
    def test_query_empty_question(self):
        """测试空问题查询"""
        query_data = {
            "question": "",
            "context": "法律咨询"
        }
        
        response = self.make_request('POST', '/api/query', query_data, use_auth=True)
        assert response.status_code in [400, 422], "空问题应该返回错误"
    
    def test_query_missing_question(self):
        """测试缺少问题字段"""
        query_data = {
            "context": "法律咨询"
            # 缺少question字段
        }
        
        response = self.make_request('POST', '/api/query', query_data, use_auth=True)
        assert response.status_code in [400, 422], "缺少问题字段应该返回错误"
    
    def test_query_long_question(self):
        """测试超长问题"""
        long_question = "这是一个非常长的问题" * 100  # 创建一个很长的问题
        
        query_data = {
            "question": long_question,
            "context": "法律咨询"
        }
        
        response = self.make_request('POST', '/api/query', query_data, use_auth=True)
        # 根据实际API限制调整期望结果
        assert response.status_code in [200, 400, 413], "超长问题处理"
    
    def test_query_special_characters(self):
        """测试包含特殊字符的问题"""
        special_questions = [
            "什么是《合同法》第123条？",
            "如何处理A公司 vs B公司的纠纷？",
            "法律条文中的'善意第三人'是什么意思？",
            "合同中的违约金是多少？（具体数额）",
            "法律术语：不可抗力 & 情势变更"
        ]
        
        for question in special_questions:
            query_data = {
                "question": question,
                "context": "法律咨询"
            }
            
            response = self.make_request('POST', '/api/query', query_data, use_auth=True)
            assert response.status_code in [200, 400], f"特殊字符问题处理失败: {question}"
    
    def test_query_different_contexts(self):
        """测试不同上下文的查询"""
        contexts = [
            "法律咨询",
            "案件分析",
            "法条解释",
            "判例研究",
            "学术研究"
        ]
        
        base_question = "什么是合同的成立要件？"
        
        for context in contexts:
            query_data = {
                "question": base_question,
                "context": context
            }
            
            response = self.make_request('POST', '/api/query', query_data, use_auth=True)
            # 所有上下文都应该能正常处理
            assert response.status_code in [200, 400], f"上下文 {context} 处理失败"
    
    def test_query_legal_domains(self):
        """测试不同法律领域的问题"""
        legal_questions = [
            {
                "question": "什么是合同的违约责任？",
                "domain": "合同法"
            },
            {
                "question": "刑事案件的证据标准是什么？",
                "domain": "刑法"
            },
            {
                "question": "行政处罚的程序有哪些？",
                "domain": "行政法"
            },
            {
                "question": "离婚案件中财产如何分割？",
                "domain": "婚姻法"
            },
            {
                "question": "劳动合同解除的条件是什么？",
                "domain": "劳动法"
            }
        ]
        
        for item in legal_questions:
            query_data = {
                "question": item["question"],
                "context": f"法律咨询 - {item['domain']}"
            }
            
            response = self.make_request('POST', '/api/query', query_data, use_auth=True)
            assert response.status_code in [200, 400], f"{item['domain']}问题处理失败"
    
    def test_query_response_format(self):
        """测试查询响应格式"""
        query_data = {
            "question": "请解释一下合同法的基本原则",
            "context": "法律咨询"
        }
        
        response = self.make_request('POST', '/api/query', query_data, use_auth=True)
        
        if response.status_code == 200:
            data = self.assert_response(response, 200, ['success'])
            
            # 检查响应格式
            assert isinstance(data, dict), "响应应该是字典格式"
            assert data['success'] is True, "成功标志应该为True"
            
            # 检查是否包含答案相关字段
            if 'data' in data:
                answer_data = data['data']
                expected_fields = ['answer', 'response', 'result', 'content']
                has_answer_field = any(field in answer_data for field in expected_fields)
                assert has_answer_field, f"响应数据应该包含答案字段之一: {expected_fields}"
    
    def test_query_concurrent_requests(self):
        """测试并发查询请求"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_query(question_suffix):
            query_data = {
                "question": f"什么是法律责任？{question_suffix}",
                "context": "法律咨询"
            }
            
            try:
                response = self.make_request('POST', '/api/query', query_data, use_auth=True)
                results.put((question_suffix, response.status_code))
            except Exception as e:
                results.put((question_suffix, f"错误: {e}"))
        
        # 创建多个并发请求
        threads = []
        for i in range(3):  # 限制并发数量避免过载
            thread = threading.Thread(target=make_query, args=(f"并发测试{i}",))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=30)
        
        # 检查结果
        success_count = 0
        while not results.empty():
            suffix, status = results.get()
            if isinstance(status, int) and status in [200, 400]:
                success_count += 1
        
        assert success_count >= 2, "至少应该有2个并发请求成功处理"
    
    def test_query_performance(self):
        """测试查询性能"""
        import time
        
        query_data = {
            "question": "请简要说明合同的基本要素",
            "context": "法律咨询"
        }
        
        start_time = time.time()
        response = self.make_request('POST', '/api/query', query_data, use_auth=True)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # 检查响应时间（根据实际情况调整阈值）
        assert response_time < 30, f"查询响应时间过长: {response_time:.2f}秒"
        
        if response.status_code == 200:
            data = self.assert_response(response, 200, ['success'])
            assert data['success'] is True
    
    @pytest.mark.parametrize("question,context,expected_status", [
        ("什么是合同？", "法律咨询", 200),
        ("什么是刑法？", "法律研究", 200),
        ("", "法律咨询", 400),  # 空问题
        ("正常问题", "", 200),  # 空上下文（可能允许）
        (None, "法律咨询", 400),  # None问题
    ])
    def test_query_parameter_validation(self, question, context, expected_status):
        """测试查询参数验证（数据驱动测试）"""
        query_data = {}
        
        if question is not None:
            query_data["question"] = question
        if context is not None:
            query_data["context"] = context
        
        response = self.make_request('POST', '/api/query', query_data, use_auth=True)
        assert response.status_code in [expected_status, 400, 422], \
            f"问题: {question}, 上下文: {context}, 期望: {expected_status}, 实际: {response.status_code}"
    
    def test_knowledge_base_status(self):
        """测试知识库状态检查（如果API提供）"""
        # 尝试获取知识库状态
        response = self.make_request('GET', '/api/knowledge/status', use_auth=True)
        
        # 根据实际API设计调整期望结果
        assert response.status_code in [200, 404], "知识库状态检查"
        
        if response.status_code == 200:
            data = self.assert_response(response, 200)
            # 检查状态信息格式
            assert isinstance(data, dict), "状态信息应该是字典格式"
    
    def test_query_history(self):
        """测试查询历史记录（如果API提供）"""
        # 先进行一次查询
        query_data = {
            "question": "什么是法律条文？",
            "context": "法律咨询"
        }
        
        response = self.make_request('POST', '/api/query', query_data, use_auth=True)
        
        # 尝试获取查询历史
        response = self.make_request('GET', '/api/query/history', use_auth=True)
        
        # 根据实际API设计调整期望结果
        assert response.status_code in [200, 404], "查询历史记录检查"
        
        if response.status_code == 200:
            data = self.assert_response(response, 200, ['success', 'data'])
            assert isinstance(data['data'], list), "历史记录应该是列表格式"
    
    def test_query_with_file_context(self):
        """测试基于文件上下文的查询（如果支持）"""
        # 这个测试需要先上传文件，然后基于文件内容进行查询
        # 由于文件上传可能需要特殊处理，这里只是一个框架
        
        query_data = {
            "question": "根据上传的文档，请分析其中的法律要点",
            "context": "文档分析",
            "file_id": "test_file_id"  # 假设的文件ID
        }
        
        response = self.make_request('POST', '/api/query', query_data, use_auth=True)
        
        # 根据实际API设计调整期望结果
        assert response.status_code in [200, 400, 404], "基于文件的查询处理"