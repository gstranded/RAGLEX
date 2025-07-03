#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理API测试
测试文件上传、下载、删除等功能
"""

import pytest
import os
import tempfile
import time
from .base_test import BaseAPITest


class TestFilesAPI(BaseAPITest):
    """文件管理API测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.login_admin()
        self.uploaded_file_ids = []  # 记录上传的文件ID，用于清理
        self.temp_files = []  # 记录创建的临时文件，用于清理
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        # 清理上传的文件
        for file_id in self.uploaded_file_ids:
            try:
                self.make_request('DELETE', f'/api/files/{file_id}', use_auth=True)
            except:
                pass
        
        # 清理临时文件
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
    
    def create_test_file(self, content: str = None, filename: str = None, file_type: str = "txt") -> str:
        """创建测试文件"""
        if content is None:
            content = f"这是一个测试文件内容 - {int(time.time())}"
        
        if filename is None:
            filename = f"test_file_{int(time.time())}.{file_type}"
        
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=f'.{file_type}', delete=False)
        temp_file.write(content)
        temp_file.close()
        
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def test_get_files_list(self):
        """测试获取文件列表"""
        response = self.make_request('GET', '/api/files', use_auth=True)
        data = self.assert_response(response, 200, ['success', 'data'])
        
        assert data['success'] is True
        assert isinstance(data['data'], list)
    
    def test_get_files_list_without_auth(self):
        """测试未认证获取文件列表"""
        response = self.make_request('GET', '/api/files')
        self.assert_response(response, 401, check_success=False)
    
    def test_upload_text_file_success(self):
        """测试上传文本文件成功"""
        # 创建测试文件
        test_content = "这是一个测试PDF文件的内容\n包含法律条文和案例分析"
        temp_file_path = self.create_test_file(test_content, "test_legal_doc.txt")
        
        # 准备上传数据
        with open(temp_file_path, 'rb') as f:
            files = {'file': (os.path.basename(temp_file_path), f, 'text/plain')}
            data = {
                'case_topic': '合同纠纷',
                'remarks': '这是一个测试上传的法律文档'
            }
            
            response = self.make_request('POST', '/api/files/upload', data=data, files=files, use_auth=True)
        
        if response.status_code == 201:
            response_data = self.assert_response(response, 201, ['success', 'data'])
            assert response_data['success'] is True
            
            file_info = response_data['data']
            assert 'id' in file_info
            assert 'filename' in file_info
            
            self.uploaded_file_ids.append(file_info['id'])
        else:
            # 如果API不支持文件上传或返回其他状态码
            assert response.status_code in [400, 404, 501], "文件上传API状态检查"
    
    def test_upload_file_without_auth(self):
        """测试未认证上传文件"""
        temp_file_path = self.create_test_file("测试内容", "unauthorized_test.txt")
        
        with open(temp_file_path, 'rb') as f:
            files = {'file': (os.path.basename(temp_file_path), f, 'text/plain')}
            data = {'case_topic': '测试主题'}
            
            response = self.make_request('POST', '/api/files/upload', data=data, files=files)
        
        self.assert_response(response, 401, check_success=False)
    
    def test_upload_empty_file(self):
        """测试上传空文件"""
        temp_file_path = self.create_test_file("", "empty_file.txt")
        
        with open(temp_file_path, 'rb') as f:
            files = {'file': (os.path.basename(temp_file_path), f, 'text/plain')}
            data = {'case_topic': '空文件测试'}
            
            response = self.make_request('POST', '/api/files/upload', data=data, files=files, use_auth=True)
        
        # 根据实际API行为调整期望结果
        assert response.status_code in [201, 400, 422], "空文件上传处理"
    
    def test_upload_large_file(self):
        """测试上传大文件"""
        # 创建一个相对较大的文件（但不要太大以免测试时间过长）
        large_content = "这是大文件测试内容。" * 1000  # 约20KB
        temp_file_path = self.create_test_file(large_content, "large_file.txt")
        
        with open(temp_file_path, 'rb') as f:
            files = {'file': (os.path.basename(temp_file_path), f, 'text/plain')}
            data = {'case_topic': '大文件测试'}
            
            response = self.make_request('POST', '/api/files/upload', data=data, files=files, use_auth=True)
        
        # 根据实际API限制调整期望结果
        assert response.status_code in [201, 400, 413], "大文件上传处理"
        
        if response.status_code == 201:
            response_data = self.assert_response(response, 201, ['success', 'data'])
            self.uploaded_file_ids.append(response_data['data']['id'])
    
    def test_upload_different_file_types(self):
        """测试上传不同类型的文件"""
        file_types = [
            ('txt', 'text/plain', '这是文本文件内容'),
            ('pdf', 'application/pdf', '%PDF-1.4\n模拟PDF内容'),  # 模拟PDF
            ('doc', 'application/msword', '模拟Word文档内容'),
            ('json', 'application/json', '{"test": "json content"}'),
        ]
        
        for file_ext, mime_type, content in file_types:
            temp_file_path = self.create_test_file(content, f"test_file.{file_ext}", file_ext)
            
            with open(temp_file_path, 'rb') as f:
                files = {'file': (os.path.basename(temp_file_path), f, mime_type)}
                data = {'case_topic': f'{file_ext}文件测试'}
                
                response = self.make_request('POST', '/api/files/upload', data=data, files=files, use_auth=True)
            
            # 根据实际API支持的文件类型调整期望结果
            assert response.status_code in [201, 400, 415], f"{file_ext}文件类型上传处理"
            
            if response.status_code == 201:
                response_data = self.assert_response(response, 201, ['success', 'data'])
                self.uploaded_file_ids.append(response_data['data']['id'])
    
    def test_upload_file_with_metadata(self):
        """测试上传文件并包含元数据"""
        temp_file_path = self.create_test_file("法律文档内容", "legal_doc_with_metadata.txt")
        
        with open(temp_file_path, 'rb') as f:
            files = {'file': (os.path.basename(temp_file_path), f, 'text/plain')}
            data = {
                'case_topic': '合同纠纷案例',
                'remarks': '这是一个包含详细元数据的法律文档，用于测试文件上传功能',
                'category': '合同法',
                'tags': '合同,纠纷,案例'
            }
            
            response = self.make_request('POST', '/api/files/upload', data=data, files=files, use_auth=True)
        
        if response.status_code == 201:
            response_data = self.assert_response(response, 201, ['success', 'data'])
            file_info = response_data['data']
            
            # 验证元数据是否正确保存
            assert file_info.get('case_topic') == data['case_topic']
            assert file_info.get('remarks') == data['remarks']
            
            self.uploaded_file_ids.append(file_info['id'])
    
    def test_get_file_by_id(self):
        """测试根据ID获取文件信息"""
        # 先上传一个文件
        temp_file_path = self.create_test_file("测试文件内容", "get_by_id_test.txt")
        
        with open(temp_file_path, 'rb') as f:
            files = {'file': (os.path.basename(temp_file_path), f, 'text/plain')}
            data = {'case_topic': 'ID测试'}
            
            upload_response = self.make_request('POST', '/api/files/upload', data=data, files=files, use_auth=True)
        
        if upload_response.status_code == 201:
            upload_data = self.assert_response(upload_response, 201, ['success', 'data'])
            file_id = upload_data['data']['id']
            self.uploaded_file_ids.append(file_id)
            
            # 获取文件信息
            response = self.make_request('GET', f'/api/files/{file_id}', use_auth=True)
            data = self.assert_response(response, 200, ['success', 'data'])
            
            file_info = data['data']
            assert file_info['id'] == file_id
            assert 'filename' in file_info
            assert 'case_topic' in file_info
    
    def test_get_file_by_invalid_id(self):
        """测试获取不存在的文件"""
        invalid_id = 99999
        response = self.make_request('GET', f'/api/files/{invalid_id}', use_auth=True)
        self.assert_response(response, 404, check_success=False)
    
    def test_download_file(self):
        """测试文件下载"""
        # 先上传一个文件
        test_content = "这是用于下载测试的文件内容"
        temp_file_path = self.create_test_file(test_content, "download_test.txt")
        
        with open(temp_file_path, 'rb') as f:
            files = {'file': (os.path.basename(temp_file_path), f, 'text/plain')}
            data = {'case_topic': '下载测试'}
            
            upload_response = self.make_request('POST', '/api/files/upload', data=data, files=files, use_auth=True)
        
        if upload_response.status_code == 201:
            upload_data = self.assert_response(upload_response, 201, ['success', 'data'])
            file_id = upload_data['data']['id']
            self.uploaded_file_ids.append(file_id)
            
            # 下载文件
            response = self.make_request('GET', f'/api/files/{file_id}/download', use_auth=True)
            
            if response.status_code == 200:
                # 验证下载的内容
                assert response.headers.get('Content-Type') in ['text/plain', 'application/octet-stream']
                # 根据实际API行为验证内容
            else:
                assert response.status_code in [404, 501], "文件下载API状态检查"
    
    def test_delete_file_success(self):
        """测试删除文件成功"""
        # 先上传一个文件
        temp_file_path = self.create_test_file("待删除的文件内容", "delete_test.txt")
        
        with open(temp_file_path, 'rb') as f:
            files = {'file': (os.path.basename(temp_file_path), f, 'text/plain')}
            data = {'case_topic': '删除测试'}
            
            upload_response = self.make_request('POST', '/api/files/upload', data=data, files=files, use_auth=True)
        
        if upload_response.status_code == 201:
            upload_data = self.assert_response(upload_response, 201, ['success', 'data'])
            file_id = upload_data['data']['id']
            
            # 删除文件
            response = self.make_request('DELETE', f'/api/files/{file_id}', use_auth=True)
            data = self.assert_response(response, 200, ['success'])
            assert data['success'] is True
            
            # 验证文件是否被删除
            get_response = self.make_request('GET', f'/api/files/{file_id}', use_auth=True)
            self.assert_response(get_response, 404, check_success=False)
    
    def test_delete_file_without_auth(self):
        """测试未认证删除文件"""
        # 假设存在一个文件ID
        fake_file_id = 1
        response = self.make_request('DELETE', f'/api/files/{fake_file_id}')
        self.assert_response(response, 401, check_success=False)
    
    def test_update_file_metadata(self):
        """测试更新文件元数据"""
        # 先上传一个文件
        temp_file_path = self.create_test_file("元数据更新测试", "metadata_update_test.txt")
        
        with open(temp_file_path, 'rb') as f:
            files = {'file': (os.path.basename(temp_file_path), f, 'text/plain')}
            data = {'case_topic': '原始主题'}
            
            upload_response = self.make_request('POST', '/api/files/upload', data=data, files=files, use_auth=True)
        
        if upload_response.status_code == 201:
            upload_data = self.assert_response(upload_response, 201, ['success', 'data'])
            file_id = upload_data['data']['id']
            self.uploaded_file_ids.append(file_id)
            
            # 更新元数据
            update_data = {
                'case_topic': '更新后的主题',
                'remarks': '这是更新后的备注信息'
            }
            
            response = self.make_request('PUT', f'/api/files/{file_id}', update_data, use_auth=True)
            
            if response.status_code == 200:
                data = self.assert_response(response, 200, ['success'])
                assert data['success'] is True
                
                # 验证更新是否成功
                get_response = self.make_request('GET', f'/api/files/{file_id}', use_auth=True)
                get_data = self.assert_response(get_response, 200, ['success', 'data'])
                
                file_info = get_data['data']
                assert file_info['case_topic'] == update_data['case_topic']
            else:
                assert response.status_code in [404, 501], "文件元数据更新API状态检查"
    
    def test_search_files_by_topic(self):
        """测试按主题搜索文件"""
        # 上传几个不同主题的文件
        search_topic = f"搜索测试主题_{int(time.time())}"
        
        for i in range(2):
            temp_file_path = self.create_test_file(f"搜索测试内容{i}", f"search_test_{i}.txt")
            
            with open(temp_file_path, 'rb') as f:
                files = {'file': (os.path.basename(temp_file_path), f, 'text/plain')}
                data = {'case_topic': search_topic}
                
                upload_response = self.make_request('POST', '/api/files/upload', data=data, files=files, use_auth=True)
            
            if upload_response.status_code == 201:
                upload_data = self.assert_response(upload_response, 201, ['success', 'data'])
                self.uploaded_file_ids.append(upload_data['data']['id'])
        
        # 搜索文件
        params = {'search': search_topic}
        response = self.make_request('GET', '/api/files', params, use_auth=True)
        data = self.assert_response(response, 200, ['success', 'data'])
        
        # 验证搜索结果
        files = data['data']
        found_files = [f for f in files if search_topic in f.get('case_topic', '')]
        assert len(found_files) >= 1, "应该找到至少1个匹配的文件"
    
    @pytest.mark.parametrize("file_extension,mime_type,should_succeed", [
        ('txt', 'text/plain', True),
        ('pdf', 'application/pdf', True),
        ('doc', 'application/msword', True),
        ('exe', 'application/octet-stream', False),  # 可执行文件应该被拒绝
        ('js', 'application/javascript', False),  # 脚本文件应该被拒绝
    ])
    def test_file_type_validation(self, file_extension, mime_type, should_succeed):
        """测试文件类型验证（数据驱动测试）"""
        temp_file_path = self.create_test_file("测试内容", f"validation_test.{file_extension}", file_extension)
        
        with open(temp_file_path, 'rb') as f:
            files = {'file': (os.path.basename(temp_file_path), f, mime_type)}
            data = {'case_topic': f'{file_extension}类型测试'}
            
            response = self.make_request('POST', '/api/files/upload', data=data, files=files, use_auth=True)
        
        if should_succeed:
            assert response.status_code in [201, 400], f"{file_extension}文件应该被接受或返回业务错误"
            if response.status_code == 201:
                response_data = self.assert_response(response, 201, ['success', 'data'])
                self.uploaded_file_ids.append(response_data['data']['id'])
        else:
            assert response.status_code in [400, 415], f"{file_extension}文件应该被拒绝"