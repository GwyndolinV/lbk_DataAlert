# LBK DataAlert 日报生成器

这是一个用于生成LBK DataAlert每日数据的工具，可以处理原始数据并生成可视化报告。

## 功能特点

- 数据处理和清洗
- 按维度聚合数据
- 创建可视化表格和图表
- 生成详细的日报

## 安装依赖

在项目根目录运行安装脚本：

```bash
python install.py
```

这将自动创建虚拟环境并安装所有必需的依赖包。

## 使用方法

1. 激活虚拟环境：

```bash
source .venv/bin/activate
```

2. 运行主程序：

```bash
python daily_report_generator.py
```

3. 使用完毕后退出虚拟环境：

```bash
deactivate
```

## 项目文件

- `daily_report_generator.py`：主程序代码
- `install.py`：依赖安装脚本
- `requirements.txt`：项目依赖列表
- `raw_data.csv`：原始数据文件
- `.gitignore`：Git忽略文件配置

## 依赖

- pandas==2.0.3
- matplotlib==3.7.2
- numpy==1.24.3