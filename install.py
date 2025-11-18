#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LBK DataAlert 项目依赖安装脚本

此Python脚本用于设置虚拟环境并安装项目所需的依赖包。
使用方法: python install.py
"""

import os
import subprocess
import sys
import time

# 设置颜色
def print_green(text):
    print("\033[0;32m" + text + "\033[0m")

def print_red(text):
    print("\033[0;31m" + text + "\033[0m")

def print_yellow(text):
    print("\033[0;33m" + text + "\033[0m")

def print_separator():
    print_green("="*50)

# 检查命令是否存在
def command_exists(cmd):
    try:
        subprocess.run([cmd, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

# 运行命令并处理错误
def run_command(cmd, shell=False):
    try:
        result = subprocess.run(cmd, shell=shell, check=True, text=True, capture_output=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print_red(f"命令执行失败: {cmd}")
        print_red(f"错误输出: {e.stderr}")
        return False, None

# 主函数
def main():
    print_separator()
    print_green("LBK DataAlert 项目依赖安装脚本")
    print_separator()
    
    # 检查Python版本
    print_yellow("检查Python版本...")
    if not command_exists("python3"):
        print_red("错误: 未找到Python3，请先安装Python 3.9或更高版本")
        return 1
    
    # 检查pip是否安装
    print_yellow("检查pip...")
    if not command_exists("pip3"):
        print_red("错误: 未找到pip3，请先安装pip")
        return 1
    
    # 检查是否在项目根目录
    print_yellow("检查项目文件...")
    if not os.path.isfile("requirements.txt"):
        print_red("错误: 未找到requirements.txt文件，请确保在项目根目录运行此脚本")
        return 1
    
    # 创建虚拟环境
    print_yellow("检查虚拟环境...")
    if not os.path.isdir(".venv"):
        print_yellow("创建虚拟环境中...")
        success, _ = run_command(["python3", "-m", "venv", ".venv"])
        if not success:
            print_red("创建虚拟环境失败")
            return 1
        print_green("虚拟环境创建成功")
    else:
        print_yellow("虚拟环境已存在，跳过创建")
    
    # 确定pip路径
    venv_pip = os.path.join(".venv", "bin", "pip")
    if not os.path.isfile(venv_pip):
        print_red(f"错误: 未找到虚拟环境中的pip: {venv_pip}")
        return 1
    
    # 更新pip
    print_yellow("更新pip...")
    success, _ = run_command([venv_pip, "install", "--upgrade", "pip"])
    if not success:
        print_red("更新pip失败")
        return 1
    
    # 安装依赖
    print_yellow("安装项目依赖中...")
    success, _ = run_command([venv_pip, "install", "-r", "requirements.txt"])
    if not success:
        print_red("安装依赖失败")
        return 1
    
    # 显示成功信息
    print_separator()
    print_green("安装完成！")
    print_separator()
    print_yellow("使用方法：")
    print_green("1. 每次使用前请先激活虚拟环境: source .venv/bin/activate")
    print_green("2. 运行主程序: python daily_report_generator.py")
    print_green("3. 完成后可退出虚拟环境: deactivate")
    print_separator()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())