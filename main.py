#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
验证码识别项目主程序入口
提供命令行界面用于演示和测试验证码识别功能
"""

import os
import argparse
import sys
from captcha_recognizer.recognizer import CaptchaRecognizer
from captcha_recognizer.utils.image_utils import preprocess_captcha


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='验证码识别工具')
    
    # 必需参数
    parser.add_argument('image', help='验证码图片路径')
    
    # 可选参数
    parser.add_argument('--type', '-t', choices=['text', 'calculation'], 
                        default='text', help='验证码类型 (默认: text)')
    
    parser.add_argument('--preprocess', '-p', action='store_true',
                        help='是否预处理图像')
    
    parser.add_argument('--grayscale', '-g', action='store_true',
                        help='转换为灰度图像')
    
    parser.add_argument('--contrast', '-c', type=float, default=2.0,
                        help='对比度增强因子 (默认: 2.0)')
    
    parser.add_argument('--sharpness', '-s', type=float, default=1.5,
                        help='锐度增强因子 (默认: 1.5)')
    
    parser.add_argument('--noise', '-n', choices=['median', 'gaussian', 'none'],
                        default='median', help='去噪方法 (默认: median)')
    
    parser.add_argument('--threshold', type=int, 
                        help='二值化阈值 (0-255), 不设置则不进行二值化')
    
    # 计算类验证码特定参数
    parser.add_argument('--return-expression', action='store_true',
                        help='返回表达式而不是计算结果 (仅适用于计算类验证码)')
    
    parser.add_argument('--as-float', action='store_true',
                        help='将计算结果作为浮点数返回 (仅适用于计算类验证码)')
    
    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 检查图片文件是否存在
    if not os.path.exists(args.image):
        print(f"错误: 图片文件不存在: {args.image}")
        sys.exit(1)
    
    try:
        # 初始化验证码识别器
        recognizer = CaptchaRecognizer()
        
        # 准备图像数据
        image_data = None
        if args.preprocess:
            # 预处理图像
            noise_method = None if args.noise == 'none' else args.noise
            image_data = preprocess_captcha(
                args.image,
                grayscale=args.grayscale,
                enhance_contrast_factor=args.contrast,
                enhance_sharpness_factor=args.sharpness,
                remove_noise_method=noise_method,
                threshold=args.threshold
            )
        
        # 准备识别参数
        recognize_kwargs = {}
        
        # 计算类验证码特定参数
        if args.type == 'calculation':
            if args.return_expression:
                recognize_kwargs['return_type'] = 'expression'
            recognize_kwargs['as_int'] = not args.as_float
        
        # 识别验证码
        result = recognizer.recognize(
            args.image if image_data is None else image_data,
            captcha_type=args.type,
            **recognize_kwargs
        )
        
        # 输出结果
        print(f"验证码识别结果: {result}")
        
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
