#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图标转换工具
将 PNG 图片转换为 ICO 格式，用于 Windows 应用程序图标
"""

import os
import sys
from PIL import Image


def convert_png_to_ico(png_path, ico_path=None, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]):
    """
    将 PNG 图片转换为 ICO 格式
    
    Args:
        png_path: PNG 文件路径
        ico_path: 输出 ICO 文件路径，如果为 None 则自动生成
        sizes: 图标尺寸列表
    """
    try:
        if not os.path.exists(png_path):
            print(f"错误: PNG 文件不存在: {png_path}")
            return False
        
        if ico_path is None:
            # 自动生成 ICO 文件路径
            base_name = os.path.splitext(png_path)[0]
            ico_path = f"{base_name}.ico"
        
        # 打开原始图片
        with Image.open(png_path) as img:
            # 确保图片有透明通道
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # 创建不同尺寸的图标
            icon_images = []
            for size in sizes:
                resized = img.resize(size, Image.Resampling.LANCZOS)
                icon_images.append(resized)
            
            # 保存为 ICO 格式（关键修复：使用各缩放图像的实际尺寸，而不是原图尺寸）
            requested_sizes = [im.size for im in icon_images]
            icon_images[0].save(ico_path, format='ICO', sizes=requested_sizes)
            print(f"成功转换: {png_path} -> {ico_path}")
            print(f"图标尺寸: {requested_sizes}")
            return True
            
    except Exception as e:
        print(f"转换失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("PNG 转 ICO 图标转换工具")
    print("=" * 50)
    
    # 检查当前目录下的 PNG 文件
    png_files = [f for f in os.listdir('.') if f.lower().endswith('.png')]
    
    if not png_files:
        print("当前目录下没有找到 PNG 文件")
        return
    
    print("找到以下 PNG 文件:")
    for i, png_file in enumerate(png_files, 1):
        print(f"{i}. {png_file}")
    
    # 让用户选择要转换的文件
    if len(png_files) == 1:
        selected_file = png_files[0]
        print(f"\n自动选择: {selected_file}")
    else:
        try:
            choice = input(f"\n请选择要转换的文件 (1-{len(png_files)}): ")
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(png_files):
                selected_file = png_files[choice_idx]
            else:
                print("无效选择")
                return
        except ValueError:
            print("无效输入")
            return
    
    # 转换文件
    print(f"\n正在转换: {selected_file}")
    success = convert_png_to_ico(selected_file)
    
    if success:
        print("\n转换完成！")
        print("\n使用说明:")
        print("1. 将生成的 .ico 文件重命名为 jerry.ico")
        print("2. 或者将 .png 文件重命名为 jerry.png")
        print("3. 重新运行 build_exe.bat 构建程序")
    else:
        print("\n转换失败，请检查文件格式")


if __name__ == "__main__":
    main()