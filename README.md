# 探索酱的小助手

一个基于 PySide6 的桌面应用程序集合，包含多个应用，方便随时增减应用。

## 项目结构

```
├── core/                    # 核心模块
│   ├── base_window.py       # 基础窗口类
│   ├── error_window.py      # 错误处理窗口
│   ├── heartbeat.py         # 定时任务支持
│   ├── widgets.py           # 通用组件
│   ├── functions.py         # 常用的函数与类
│   ├── user_interface.py    # 用户界面相关类
│   ├── global_constants.py  # 全局常量
│   └── notification.py      # 通知系统单例
├── homepage/                # 主页面
│   ├── main_window.py       # 主窗口
│   └── widgets.py           # 主页组件
├── apps/                    # 应用模块
│   ├── __init__.py          # 应用配置
│   ├── <app_name>/          # 各应用的模块
│   │   ├── __init__.py      # 应用入口
│   │   ├── data/            # 应用数据目录（不会被同步到代码库）
│   │   └── <other files>    # 其他本应用相关文件
├── assets/                  # 资源文件
│   ├── svg/                 # SVG 图标
│   ├── logo.ico             # 应用图标
│   └── logo.png             # PNG 图标
├── data/                    # 数据目录（不会被同步到代码库）
├── docs/                    # 文档
│   └── roadmap.md           # 项目路线图
├── run.py                   # 主程序入口
├── run_app.py               # 单独启动指定应用
├── start.bat                # Windows启动脚本（无命令行窗口）
└── requirements.txt         # 依赖包列表
```

## 运行方式

### 方式一：启动主程序

```bash
python run.py
```

### 方式二：单独启动指定应用

```bash
python run_app.py <app_name>
```

示例：
```bash
python run_app.py calendar    # 启动日程应用
python run_app.py tasks       # 启动任务应用
```

### 方式三：Windows 双击启动

直接双击 `start.bat` 文件，不会产生命令行窗口。

## 技术栈

- **框架**: PySide6 (Qt6 Python 绑定)
- **语言**: Python 3.x
- **图标**: 自定义 ICO/PNG/SVG 图标

## 开发说明

### 添加新应用

在 `apps/__init__.py` 中添加应用配置：

```python
APP_LIST = {
    "your_app": {
        "display_name": "应用显示名称",
        "window": lambda: import_module('apps.your_app').YourWindowClass(),
        "icon": "apps/your_app/assets/icon.ico"  # 可选：自定义图标路径
    }
}
```

**配置键说明**：

| 键 | 类型 | 必填 | 说明 |
|----|------|------|------|
| `display_name` | str | 是 | 应用显示名称 |
| `window` | callable | 是 | 返回窗口实例的 lambda 函数 |
| `icon` | str | 否 | 自定义图标文件路径 |

2. 新应用如有窗口，应继承 `core.base_window.BaseWindow` 或 `BaseDialog`。

## 注意事项

- 数据文件存储在各应用的 `data/` 目录下，这些目录下的数据不会被同步到代码库中。
- 首次运行某些应用会自动创建初始数据。
