import json
import os

SETTINGS_FILE = "data/settings.json"


def load_settings():
    """
    从 data/settings.json 加载设置数据

    Returns:
        dict: 设置数据字典，如果文件不存在则返回空字典
    """
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_settings(data):
    """
    将设置数据保存到 data/settings.json

    Parameters:
        data (dict): 要保存的设置数据
    """
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_setting_value(json_path, default=None):
    """
    获取指定路径的设置值

    Parameters:
        json_path (str): JSON路径，如 "news_monitor.activated"
        default: 默认值，当路径不存在时返回

    Returns:
        设置值或默认值
    """
    data = load_settings()
    keys = json_path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def set_setting_value(json_path, value):
    """
    设置指定路径的设置值

    Parameters:
        json_path (str): JSON路径，如 "news_monitor.activated"
        value: 要设置的值
    """
    data = load_settings()
    keys = json_path.split('.')
    current = data
    
    for i, key in enumerate(keys[:-1]):
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value
    save_settings(data)