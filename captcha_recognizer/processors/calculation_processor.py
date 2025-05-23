#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
计算类验证码处理器
处理需要进行数学计算的验证码，如"1+2=?"
"""

import re
from typing import Union, Dict, Any, Optional, Tuple


class CalculationCaptchaProcessor:
    """
    计算类验证码处理器
    处理需要进行数学计算的验证码
    """
    
    def __init__(self, ocr_engine):
        """
        初始化计算类验证码处理器
        
        Args:
            ocr_engine: OCR引擎实例
        """
        self.ocr = ocr_engine
        
        # 支持的运算符
        self.operators = {
            '+': lambda x, y: x + y,
            '-': lambda x, y: x - y,
            '*': lambda x, y: x * y,
            'x': lambda x, y: x * y,  # 有时'x'被用作乘法符号
            '×': lambda x, y: x * y,  # 全角乘法符号
            '/': lambda x, y: x / y if y != 0 else float('inf'),
            '÷': lambda x, y: x / y if y != 0 else float('inf'),  # 除法符号
        }
    
    def process(self, image_data: bytes, **kwargs) -> str:
        """
        处理计算类验证码
        
        Args:
            image_data: 验证码图片的字节数据
            **kwargs: 额外参数
                - return_type: 返回类型，可以是'result'(默认)或'expression'
                - as_int: 是否将结果转为整数，默认为True
            
        Returns:
            计算结果或表达式字符串
        """
        # 获取OCR识别结果
        text = self.ocr.classification(image_data)
        
        # 清理文本
        text = self._clean_text(text)
        
        # 解析表达式
        expression, result = self._parse_expression(text)
        
        # 确定返回类型
        return_type = kwargs.get('return_type', 'result')
        as_int = kwargs.get('as_int', True)
        
        if return_type == 'expression':
            return expression
        else:
            # 返回计算结果
            if as_int and isinstance(result, float) and result.is_integer():
                return str(int(result))
            return str(result)
    
    def _clean_text(self, text: str) -> str:
        """
        清理OCR识别的文本
        
        Args:
            text: OCR识别的原始文本
            
        Returns:
            清理后的文本
        """
        # 移除空格
        text = text.replace(' ', '')
        
        # 替换常见的OCR错误
        replacements = {
            'O': '0',
            'o': '0',
            'l': '1',
            'I': '1',
            'S': '5',
            'Z': '2',
            'B': '8',
            '?': '',  # 移除问号
            '=': '',  # 移除等号
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def _parse_expression(self, text: str) -> Tuple[str, float]:
        """
        解析数学表达式
        
        Args:
            text: 清理后的文本
            
        Returns:
            表达式字符串和计算结果
        """
        # 使用正则表达式提取数字和运算符
        # 匹配模式：数字后跟运算符后跟数字
        pattern = r'(\d+)([+\-*/x×÷])(\d+)'
        match = re.search(pattern, text)
        
        if match:
            num1 = int(match.group(1))
            operator = match.group(2)
            num2 = int(match.group(3))
            
            # 构建表达式字符串
            expression = f"{num1}{operator}{num2}"
            
            # 计算结果
            if operator in self.operators:
                result = self.operators[operator](num1, num2)
                return expression, result
        
        # 如果无法解析，返回原文本和None
        return text, None
