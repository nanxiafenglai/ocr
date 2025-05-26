#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
分类型验证码API测试工具
测试各种验证码类型的专门接口
"""

import requests
import json
import time
import base64
import os
from typing import Dict, Any


class TypedAPITester:
    """分类型API测试器"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """初始化测试器"""
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TypedCaptchaAPI-Tester/1.0'
        })
    
    def test_health(self) -> Dict[str, Any]:
        """测试健康检查"""
        print("🔍 测试健康检查...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 健康检查成功")
                print(f"   版本: {data.get('version')}")
                print(f"   支持类型: {len(data.get('supported_types', {}))}")
                print(f"   输入方式: {', '.join(data.get('input_methods', []))}")
                return {"success": True, "data": data}
            else:
                print(f"❌ 健康检查失败: HTTP {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ 健康检查异常: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def test_digit_recognition(self) -> Dict[str, Any]:
        """测试纯数字验证码识别"""
        print("\n🔢 测试纯数字验证码识别...")
        
        # 测试已知的数字验证码
        test_files = [
            "ocr-main/ocr-main/examples/OIP-C.jpg",
            "ocr-main/ocr-main/examples/url_captcha.jpg"
        ]
        
        results = []
        
        for file_path in test_files:
            if os.path.exists(file_path):
                try:
                    # 文件上传测试
                    with open(file_path, 'rb') as f:
                        files = {'file': f}
                        
                        start_time = time.time()
                        response = self.session.post(
                            f"{self.base_url}/api/digit/recognize/upload",
                            files=files,
                            timeout=60
                        )
                        request_time = round((time.time() - start_time) * 1000, 2)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            print(f"   ✅ {os.path.basename(file_path)}: '{data.get('result')}' ({request_time}ms)")
                            results.append({
                                "file": os.path.basename(file_path),
                                "result": data.get('result'),
                                "success": True
                            })
                        else:
                            print(f"   ❌ {os.path.basename(file_path)}: {data.get('error')}")
                            results.append({
                                "file": os.path.basename(file_path),
                                "error": data.get('error'),
                                "success": False
                            })
                    else:
                        print(f"   ❌ {os.path.basename(file_path)}: HTTP {response.status_code}")
                        results.append({
                            "file": os.path.basename(file_path),
                            "error": f"HTTP {response.status_code}",
                            "success": False
                        })
                        
                except Exception as e:
                    print(f"   ❌ {os.path.basename(file_path)}: {str(e)}")
                    results.append({
                        "file": os.path.basename(file_path),
                        "error": str(e),
                        "success": False
                    })
        
        return {"success": len(results) > 0, "results": results}
    
    def test_mixed_recognition(self) -> Dict[str, Any]:
        """测试数字字母混合验证码识别"""
        print("\n🔤 测试数字字母混合验证码识别...")
        
        # 测试已知的混合验证码
        test_files = [
            "ocr-main/ocr-main/examples/image.png"
        ]
        
        results = []
        
        for file_path in test_files:
            if os.path.exists(file_path):
                try:
                    # 文件上传测试
                    with open(file_path, 'rb') as f:
                        files = {'file': f}
                        
                        start_time = time.time()
                        response = self.session.post(
                            f"{self.base_url}/api/mixed/recognize/upload",
                            files=files,
                            timeout=60
                        )
                        request_time = round((time.time() - start_time) * 1000, 2)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            print(f"   ✅ {os.path.basename(file_path)}: '{data.get('result')}' ({request_time}ms)")
                            results.append({
                                "file": os.path.basename(file_path),
                                "result": data.get('result'),
                                "success": True
                            })
                        else:
                            print(f"   ❌ {os.path.basename(file_path)}: {data.get('error')}")
                            results.append({
                                "file": os.path.basename(file_path),
                                "error": data.get('error'),
                                "success": False
                            })
                    else:
                        print(f"   ❌ {os.path.basename(file_path)}: HTTP {response.status_code}")
                        results.append({
                            "file": os.path.basename(file_path),
                            "error": f"HTTP {response.status_code}",
                            "success": False
                        })
                        
                except Exception as e:
                    print(f"   ❌ {os.path.basename(file_path)}: {str(e)}")
                    results.append({
                        "file": os.path.basename(file_path),
                        "error": str(e),
                        "success": False
                    })
        
        return {"success": len(results) > 0, "results": results}
    
    def test_auto_recognition(self) -> Dict[str, Any]:
        """测试自动类型识别"""
        print("\n🤖 测试自动类型识别...")
        
        # 测试所有验证码文件
        test_files = [
            ("ocr-main/ocr-main/examples/image.png", "mixed_alphanumeric"),
            ("ocr-main/ocr-main/examples/OIP-C.jpg", "pure_digit"),
            ("ocr-main/ocr-main/examples/url_captcha.jpg", "pure_digit")
        ]
        
        results = []
        
        for file_path, expected_type in test_files:
            if os.path.exists(file_path):
                try:
                    # 文件上传测试
                    with open(file_path, 'rb') as f:
                        files = {'file': f}
                        
                        start_time = time.time()
                        response = self.session.post(
                            f"{self.base_url}/api/auto/recognize/upload",
                            files=files,
                            timeout=60
                        )
                        request_time = round((time.time() - start_time) * 1000, 2)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            result = data.get('result')
                            detected_type = data.get('captcha_type')
                            type_correct = detected_type == expected_type
                            
                            status = "✅" if type_correct else "⚠️"
                            print(f"   {status} {os.path.basename(file_path)}: '{result}' -> {detected_type}")
                            
                            results.append({
                                "file": os.path.basename(file_path),
                                "result": result,
                                "detected_type": detected_type,
                                "expected_type": expected_type,
                                "type_correct": type_correct,
                                "success": True
                            })
                        else:
                            print(f"   ❌ {os.path.basename(file_path)}: {data.get('error')}")
                            results.append({
                                "file": os.path.basename(file_path),
                                "error": data.get('error'),
                                "success": False
                            })
                    else:
                        print(f"   ❌ {os.path.basename(file_path)}: HTTP {response.status_code}")
                        results.append({
                            "file": os.path.basename(file_path),
                            "error": f"HTTP {response.status_code}",
                            "success": False
                        })
                        
                except Exception as e:
                    print(f"   ❌ {os.path.basename(file_path)}: {str(e)}")
                    results.append({
                        "file": os.path.basename(file_path),
                        "error": str(e),
                        "success": False
                    })
        
        return {"success": len(results) > 0, "results": results}
    
    def test_url_recognition(self) -> Dict[str, Any]:
        """测试URL识别"""
        print("\n🌐 测试URL识别...")
        
        # 测试URL
        test_url = "https://ts1.tc.mm.bing.net/th/id/R-C.3aba72e96a9d1c073deda349b83f0f5b?rik=gS9sJR0bF5TGAA&riu=http%3a%2f%2fimg-03.proxy.5ce.com%2fview%2fimage%3f%26type%3d2%26guid%3de4e5833c-cf2f-eb11-8da9-e4434bdf6706%26url%3dhttps%3a%2f%2fpic3.zhimg.com%2fv2-17a03b9627aa8f850628c14550a0544a_b.jpg&ehk=4%2bX2KfJFsAZXJ1J1WbafyCUJaWS5Fy0fnQHlahF1gxg%3d&risl=&pid=ImgRaw&r=0"
        
        try:
            payload = {"url": test_url}
            
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/api/digit/recognize/url",
                json=payload,
                timeout=60
            )
            request_time = round((time.time() - start_time) * 1000, 2)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"   ✅ URL识别成功: '{data.get('result')}' ({request_time}ms)")
                    return {"success": True, "result": data.get('result')}
                else:
                    print(f"   ❌ URL识别失败: {data.get('error')}")
                    return {"success": False, "error": data.get('error')}
            else:
                print(f"   ❌ URL识别失败: HTTP {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"   ❌ URL识别异常: {str(e)}")
            return {"success": False, "error": str(e)}


def main():
    """主测试函数"""
    print("🚀 分类型验证码识别API测试")
    print("=" * 60)
    
    # 创建测试器
    tester = TypedAPITester()
    
    results = {}
    
    # 1. 健康检查测试
    results['health'] = tester.test_health()
    
    # 2. 纯数字验证码测试
    results['digit'] = tester.test_digit_recognition()
    
    # 3. 数字字母混合测试
    results['mixed'] = tester.test_mixed_recognition()
    
    # 4. 自动类型识别测试
    results['auto'] = tester.test_auto_recognition()
    
    # 5. URL识别测试
    results['url'] = tester.test_url_recognition()
    
    # 测试结果汇总
    print("\n" + "="*60)
    print("📊 测试结果汇总:")
    print("="*60)
    
    success_count = 0
    total_count = 0
    
    for test_name, result in results.items():
        total_count += 1
        if result.get('success'):
            success_count += 1
            print(f"✅ {test_name}: 成功")
        else:
            print(f"❌ {test_name}: 失败 - {result.get('error', '未知错误')}")
    
    print(f"\n🎯 总体成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("🎉 所有测试通过！分类型API功能完全正常！")
    else:
        print("⚠️ 部分测试失败，请检查API服务状态")
    
    # 详细结果分析
    print(f"\n📋 详细结果分析:")
    print("-" * 40)
    
    if results.get('auto', {}).get('success'):
        auto_results = results['auto']['results']
        type_accuracy = sum(1 for r in auto_results if r.get('type_correct', False)) / len(auto_results) * 100
        print(f"🤖 自动类型识别准确率: {type_accuracy:.1f}%")
    
    if results.get('digit', {}).get('success'):
        digit_results = results['digit']['results']
        digit_success = sum(1 for r in digit_results if r.get('success', False))
        print(f"🔢 数字验证码识别成功率: {digit_success}/{len(digit_results)}")
    
    if results.get('mixed', {}).get('success'):
        mixed_results = results['mixed']['results']
        mixed_success = sum(1 for r in mixed_results if r.get('success', False))
        print(f"🔤 混合验证码识别成功率: {mixed_success}/{len(mixed_results)}")


if __name__ == "__main__":
    main()
