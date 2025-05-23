#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
验证码识别器测试用例
"""

import os
import unittest
from PIL import Image, ImageDraw, ImageFont
import io
import random
import string

from captcha_recognizer.recognizer import CaptchaRecognizer
from captcha_recognizer.utils.image_utils import preprocess_captcha


class TestCaptchaRecognizer(unittest.TestCase):
    """验证码识别器测试类"""

    @classmethod
    def setUpClass(cls):
        """测试前的准备工作"""
        # 初始化验证码识别器
        cls.recognizer = CaptchaRecognizer()

        # 创建测试图片目录
        cls.test_dir = os.path.join(os.path.dirname(__file__), 'test_images')
        os.makedirs(cls.test_dir, exist_ok=True)

        # 生成测试图片
        cls.text_captcha_path = os.path.join(cls.test_dir, 'text_captcha.png')
        cls.calc_captcha_path = os.path.join(cls.test_dir, 'calc_captcha.png')

        # 生成文字验证码
        cls.text_content = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        cls._generate_text_captcha(cls.text_captcha_path, cls.text_content)

        # 生成计算验证码
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        cls.calc_content = f"{num1}+{num2}"
        cls.calc_result = str(num1 + num2)
        cls._generate_text_captcha(cls.calc_captcha_path, cls.calc_content)

    @classmethod
    def tearDownClass(cls):
        """测试后的清理工作"""
        # 删除测试图片
        if os.path.exists(cls.text_captcha_path):
            os.remove(cls.text_captcha_path)
        if os.path.exists(cls.calc_captcha_path):
            os.remove(cls.calc_captcha_path)

        # 尝试删除测试目录
        try:
            os.rmdir(cls.test_dir)
        except OSError:
            pass  # 目录可能不为空

    @classmethod
    def _generate_text_captcha(cls, path, text, width=100, height=40):
        """生成文字验证码图片"""
        # 创建空白图像
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)

        try:
            # 尝试加载字体
            font = ImageFont.truetype("arial.ttf", 24)
        except IOError:
            # 如果找不到字体，使用默认字体
            font = ImageFont.load_default()

        # 计算文本位置
        try:
            # 新版PIL使用font.getbbox
            left, top, right, bottom = font.getbbox(text)
            text_width, text_height = right - left, bottom - top
        except AttributeError:
            # 旧版PIL使用textsize
            try:
                text_width, text_height = draw.textsize(text, font=font)
            except AttributeError:
                # 如果两种方法都不可用，使用估计值
                text_width, text_height = len(text) * 15, 24

        position = ((width - text_width) // 2, (height - text_height) // 2)

        # 绘制文本
        draw.text(position, text, font=font, fill=(0, 0, 0))

        # 添加一些噪点
        for _ in range(100):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            draw.point((x, y), fill=(random.randint(0, 255),
                                     random.randint(0, 255),
                                     random.randint(0, 255)))

        # 保存图像
        image.save(path)

    def test_text_captcha_recognition(self):
        """测试文字验证码识别"""
        # 使用样例图片
        examples_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples')
        sample_path = os.path.join(examples_dir, 'text_captcha.png')

        if os.path.exists(sample_path):
            # 识别样例图片
            result = self.recognizer.recognize(sample_path, captcha_type='text')
            self.assertIsNotNone(result)
            self.assertIsInstance(result, str)
            print(f"样例文字验证码识别结果: {result}")

        # 识别生成的测试图片
        result = self.recognizer.recognize(self.text_captcha_path, captcha_type='text')
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        print(f"生成的文字验证码内容: {self.text_content}, 识别结果: {result}")

    def test_calculation_captcha_recognition(self):
        """测试计算类验证码识别"""
        # 识别生成的计算验证码
        result = self.recognizer.recognize(self.calc_captcha_path, captcha_type='calculation')
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        print(f"生成的计算验证码内容: {self.calc_content}, 期望结果: {self.calc_result}, 识别结果: {result}")

        # 测试返回表达式
        expression = self.recognizer.recognize(
            self.calc_captcha_path,
            captcha_type='calculation',
            return_type='expression'
        )
        self.assertIsNotNone(expression)
        self.assertIsInstance(expression, str)
        print(f"计算验证码表达式: {expression}")

    def test_image_preprocessing(self):
        """测试图像预处理"""
        # 预处理图像
        processed_data = preprocess_captcha(
            self.text_captcha_path,
            grayscale=True,
            enhance_contrast_factor=2.0,
            enhance_sharpness_factor=1.5,
            remove_noise_method='median',
            threshold=128
        )

        # 使用预处理后的图像进行识别
        result = self.recognizer.recognize(processed_data, captcha_type='text')
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        print(f"预处理后的文字验证码识别结果: {result}")

    def test_different_image_formats(self):
        """测试不同的图像格式"""
        # 加载图像
        image = Image.open(self.text_captcha_path)

        # 测试PIL图像对象
        result1 = self.recognizer.recognize(image, captcha_type='text')
        self.assertIsNotNone(result1)

        # 测试字节数据
        with open(self.text_captcha_path, 'rb') as f:
            image_bytes = f.read()
        result2 = self.recognizer.recognize(image_bytes, captcha_type='text')
        self.assertIsNotNone(result2)

        # 测试文件路径
        result3 = self.recognizer.recognize(self.text_captcha_path, captcha_type='text')
        self.assertIsNotNone(result3)

        print(f"不同格式的识别结果 - PIL: {result1}, 字节: {result2}, 路径: {result3}")


if __name__ == '__main__':
    unittest.main()
