#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Flask API服务
提供验证码识别的RESTful API
"""

import os
import time
import base64
import io
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import requests
from PIL import Image

from captcha_recognizer.recognizer import CaptchaRecognizer
from captcha_recognizer.utils.image_utils import preprocess_captcha


# 创建Flask应用
app = Flask(__name__)

# 配置
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB
app.config['UPLOAD_FOLDER'] = 'temp_uploads'  # 临时上传目录
app.config['API_VERSION'] = '1.0.0'

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 全局变量
START_TIME = time.time()
recognizer = CaptchaRecognizer()


def get_uptime():
    """获取服务运行时间（秒）"""
    return time.time() - START_TIME


def process_image_file(file):
    """
    处理上传的图像文件
    
    Args:
        file: 上传的文件对象
        
    Returns:
        图像的字节数据
    """
    # 保存文件
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # 读取文件内容
    with open(filepath, 'rb') as f:
        image_data = f.read()
    
    # 验证是否为有效的图像
    try:
        Image.open(io.BytesIO(image_data))
    except Exception as e:
        raise ValueError(f"无效的图像文件: {str(e)}")
    
    # 删除临时文件
    os.remove(filepath)
    
    return image_data


def fetch_image_from_url(url):
    """
    从URL获取图像
    
    Args:
        url: 图像URL
        
    Returns:
        图像的字节数据
    """
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        raise ValueError(f"无法从URL获取图像: {response.status_code}")
    
    image_data = response.content
    
    # 验证是否为有效的图像
    try:
        Image.open(io.BytesIO(image_data))
    except Exception as e:
        raise ValueError(f"URL指向的不是有效的图像: {str(e)}")
    
    return image_data


def decode_base64_image(base64_string):
    """
    解码Base64编码的图像数据
    
    Args:
        base64_string: Base64编码的图像数据
        
    Returns:
        解码后的图像字节数据
    """
    # 处理可能的数据URL格式
    if ',' in base64_string:
        base64_string = base64_string.split(',', 1)[1]
    
    try:
        image_data = base64.b64decode(base64_string)
    except Exception as e:
        raise ValueError(f"无效的Base64编码: {str(e)}")
    
    # 验证是否为有效的图像
    try:
        Image.open(io.BytesIO(image_data))
    except Exception as e:
        raise ValueError(f"无效的Base64图像数据: {str(e)}")
    
    return image_data


def apply_preprocessing(image_data, params):
    """
    应用图像预处理
    
    Args:
        image_data: 图像字节数据
        params: 预处理参数字典
        
    Returns:
        处理后的图像字节数据
    """
    if not params.get('preprocess', False):
        return image_data
    
    return preprocess_captcha(
        image_data,
        grayscale=params.get('grayscale', False),
        enhance_contrast_factor=params.get('contrast'),
        enhance_sharpness_factor=params.get('sharpness'),
        remove_noise_method=params.get('noise_method'),
        threshold=params.get('threshold')
    )


def prepare_recognition_kwargs(captcha_type, params):
    """
    准备识别参数
    
    Args:
        captcha_type: 验证码类型
        params: 参数字典
        
    Returns:
        识别参数字典
    """
    kwargs = {}
    
    if captcha_type == "calculation":
        if params.get('return_expression', False):
            kwargs['return_type'] = 'expression'
        kwargs['as_int'] = not params.get('as_float', False)
    
    return kwargs


def recognize_captcha(image_data, captcha_type, params):
    """
    识别验证码
    
    Args:
        image_data: 图像字节数据
        captcha_type: 验证码类型
        params: 参数字典
        
    Returns:
        识别结果和处理时间（毫秒）
    """
    start_time = time.time()
    
    # 应用预处理
    if params.get('preprocess', False):
        image_data = apply_preprocessing(image_data, params)
    
    # 准备识别参数
    kwargs = prepare_recognition_kwargs(captcha_type, params)
    
    # 识别验证码
    result = recognizer.recognize(
        image_data,
        captcha_type=captcha_type,
        **kwargs
    )
    
    # 计算处理时间（毫秒）
    processing_time = (time.time() - start_time) * 1000
    
    return result, processing_time


@app.route('/')
def index():
    """根路径，重定向到API文档"""
    return """
    <h1>验证码识别API</h1>
    <p>API端点:</p>
    <ul>
        <li><a href="/api/health">/api/health</a> - 健康检查</li>
        <li>/api/recognize/upload - 上传图片识别</li>
        <li>/api/recognize/url - URL图片识别</li>
        <li>/api/recognize/base64 - Base64图片识别</li>
    </ul>
    """


@app.route('/api/health')
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "ok",
        "version": app.config['API_VERSION'],
        "uptime": get_uptime()
    })


@app.route('/api/recognize/upload', methods=['POST'])
def recognize_upload():
    """通过文件上传识别验证码"""
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "未提供文件"
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "未选择文件"
            }), 400
        
        # 获取参数
        captcha_type = request.form.get('captcha_type', 'text')
        if captcha_type not in ['text', 'calculation']:
            return jsonify({
                "success": False,
                "error": f"不支持的验证码类型: {captcha_type}"
            }), 400
        
        # 处理参数
        params = {
            'preprocess': request.form.get('preprocess', 'false').lower() == 'true',
            'grayscale': request.form.get('grayscale', 'false').lower() == 'true',
            'contrast': float(request.form.get('contrast')) if request.form.get('contrast') else None,
            'sharpness': float(request.form.get('sharpness')) if request.form.get('sharpness') else None,
            'noise_method': request.form.get('noise_method'),
            'threshold': int(request.form.get('threshold')) if request.form.get('threshold') else None,
            'return_expression': request.form.get('return_expression', 'false').lower() == 'true',
            'as_float': request.form.get('as_float', 'false').lower() == 'true'
        }
        
        # 处理图像
        image_data = process_image_file(file)
        
        # 识别验证码
        result, processing_time = recognize_captcha(image_data, captcha_type, params)
        
        return jsonify({
            "success": True,
            "result": result,
            "processing_time": processing_time
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/recognize/url', methods=['POST'])
def recognize_url():
    """通过URL识别验证码"""
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({
                "success": False,
                "error": "未提供URL"
            }), 400
        
        url = data['url']
        captcha_type = data.get('captcha_type', 'text')
        if captcha_type not in ['text', 'calculation']:
            return jsonify({
                "success": False,
                "error": f"不支持的验证码类型: {captcha_type}"
            }), 400
        
        # 获取图像
        image_data = fetch_image_from_url(url)
        
        # 识别验证码
        result, processing_time = recognize_captcha(image_data, captcha_type, data)
        
        return jsonify({
            "success": True,
            "result": result,
            "processing_time": processing_time
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/recognize/base64', methods=['POST'])
def recognize_base64():
    """通过Base64编码数据识别验证码"""
    try:
        data = request.json
        if not data or 'image_data' not in data:
            return jsonify({
                "success": False,
                "error": "未提供图像数据"
            }), 400
        
        image_data_base64 = data['image_data']
        captcha_type = data.get('captcha_type', 'text')
        if captcha_type not in ['text', 'calculation']:
            return jsonify({
                "success": False,
                "error": f"不支持的验证码类型: {captcha_type}"
            }), 400
        
        # 解码图像
        image_data = decode_base64_image(image_data_base64)
        
        # 识别验证码
        result, processing_time = recognize_captcha(image_data, captcha_type, data)
        
        return jsonify({
            "success": True,
            "result": result,
            "processing_time": processing_time
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    # 启动Flask应用
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
