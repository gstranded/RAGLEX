#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行脚本
用于执行所有测试并生成报告
"""

import os
import sys
import time
import argparse
import subprocess
from typing import List, Dict, Any
from test_config import config


class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.results = {}
        self.failed_tests = []
        self.passed_tests = []
        
    def run_pytest(self, test_files: List[str] = None, verbose: bool = True, 
                   coverage: bool = False, html_report: bool = False) -> int:
        """使用pytest运行测试"""
        cmd = ['python', '-m', 'pytest']
        
        # 添加测试文件
        if test_files:
            cmd.extend(test_files)
        else:
            cmd.append('.')
        
        # 添加选项
        if verbose:
            cmd.append('-v')
        
        if coverage:
            cmd.extend(['--cov=../app', '--cov-report=term-missing'])
            if html_report:
                cmd.append('--cov-report=html')
        
        # 添加其他有用的选项
        cmd.extend([
            '--tb=short',  # 简短的错误回溯
            '--strict-markers',  # 严格的标记模式
            '-x',  # 遇到第一个失败就停止
        ])
        
        print(f"运行命令: {' '.join(cmd)}")
        print(f"测试环境: {config.get_environment_info()}")
        print("-" * 60)
        
        self.start_time = time.time()
        
        try:
            result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
            return result.returncode
        except Exception as e:
            print(f"运行pytest时出错: {e}")
            return 1
        finally:
            self.end_time = time.time()
    
    def run_manual_tests(self) -> Dict[str, Any]:
        """运行手动测试（不使用pytest）"""
        print("开始运行手动测试...")
        print(f"测试环境: {config.BASE_URL}")
        print("-" * 60)
        
        self.start_time = time.time()
        
        # 导入测试模块
        test_modules = [
            ('认证API测试', 'test_auth'),
            ('案件管理API测试', 'test_cases'),
            ('知识库API测试', 'test_knowledge'),
            ('文件管理API测试', 'test_files')
        ]
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for module_name, module_file in test_modules:
            print(f"\n运行 {module_name}...")
            try:
                # 动态导入测试模块
                module = __import__(module_file)
                
                # 获取测试类
                test_classes = []
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        attr_name.startswith('Test') and 
                        hasattr(attr, 'setup_method')):
                        test_classes.append(attr)
                
                # 运行测试类中的测试方法
                for test_class in test_classes:
                    test_instance = test_class()
                    
                    # 获取测试方法
                    test_methods = [method for method in dir(test_instance) 
                                  if method.startswith('test_')]
                    
                    for method_name in test_methods:
                        total_tests += 1
                        method = getattr(test_instance, method_name)
                        
                        try:
                            # 运行setup
                            if hasattr(test_instance, 'setup_method'):
                                test_instance.setup_method()
                            
                            # 运行测试方法
                            print(f"  运行 {method_name}...", end='')
                            method()
                            print(" ✓ 通过")
                            passed_tests += 1
                            self.passed_tests.append(f"{test_class.__name__}.{method_name}")
                            
                        except Exception as e:
                            print(f" ✗ 失败: {str(e)}")
                            failed_tests += 1
                            self.failed_tests.append({
                                'test': f"{test_class.__name__}.{method_name}",
                                'error': str(e)
                            })
                        
                        finally:
                            # 运行teardown
                            if hasattr(test_instance, 'teardown_method'):
                                try:
                                    test_instance.teardown_method()
                                except:
                                    pass
                
            except Exception as e:
                print(f"导入模块 {module_file} 失败: {e}")
                failed_tests += 1
        
        self.end_time = time.time()
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'duration': self.end_time - self.start_time
        }
    
    def check_server_health(self) -> bool:
        """检查服务器健康状态"""
        try:
            import requests
            response = requests.get(f"{config.BASE_URL}/api/health", timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"服务器健康检查失败: {e}")
            return False
    
    def generate_report(self, results: Dict[str, Any] = None):
        """生成测试报告"""
        print("\n" + "="*60)
        print("测试报告")
        print("="*60)
        
        if results:
            duration = results['duration']
            print(f"总测试数: {results['total']}")
            print(f"通过: {results['passed']}")
            print(f"失败: {results['failed']}")
            print(f"成功率: {results['passed']/results['total']*100:.1f}%")
            print(f"运行时间: {duration:.2f}秒")
        
        if self.failed_tests:
            print("\n失败的测试:")
            for i, failed_test in enumerate(self.failed_tests, 1):
                if isinstance(failed_test, dict):
                    print(f"{i}. {failed_test['test']}: {failed_test['error']}")
                else:
                    print(f"{i}. {failed_test}")
        
        print(f"\n测试环境信息:")
        env_info = config.get_environment_info()
        for key, value in env_info.items():
            print(f"  {key}: {value}")
        
        print("\n" + "="*60)
    
    def setup_test_environment(self):
        """设置测试环境"""
        print("设置测试环境...")
        
        # 检查必要的依赖
        required_packages = ['requests', 'pytest']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"缺少必要的包: {', '.join(missing_packages)}")
            print("请运行: pip install " + ' '.join(missing_packages))
            return False
        
        # 检查服务器状态
        print(f"检查服务器状态: {config.BASE_URL}")
        if not self.check_server_health():
            print("警告: 服务器健康检查失败，测试可能会失败")
            return False
        
        print("测试环境设置完成")
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='RAGLEX API测试运行器')
    parser.add_argument('--mode', choices=['pytest', 'manual'], default='manual',
                       help='测试运行模式')
    parser.add_argument('--files', nargs='*', help='指定要运行的测试文件')
    parser.add_argument('--coverage', action='store_true', help='生成覆盖率报告')
    parser.add_argument('--html', action='store_true', help='生成HTML报告')
    parser.add_argument('--verbose', action='store_true', default=True, help='详细输出')
    parser.add_argument('--skip-setup', action='store_true', help='跳过环境设置检查')
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # 设置测试环境
    if not args.skip_setup:
        if not runner.setup_test_environment():
            print("测试环境设置失败，退出")
            sys.exit(1)
    
    # 运行测试
    if args.mode == 'pytest':
        print("使用pytest运行测试...")
        exit_code = runner.run_pytest(
            test_files=args.files,
            verbose=args.verbose,
            coverage=args.coverage,
            html_report=args.html
        )
        sys.exit(exit_code)
    else:
        print("使用手动模式运行测试...")
        results = runner.run_manual_tests()
        runner.generate_report(results)
        
        # 根据测试结果设置退出码
        if results['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == '__main__':
    main()