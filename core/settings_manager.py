import json
import os

from glom import glom, Assign


SETTINGS_FILE = "data/settings.json"


class SettingsManager:
    """单例设置数据管理器，初始化时从 data/settings.json 加载数据到内存"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._settings_file = SETTINGS_FILE
        self.data = {}
        self.reload()
        self._initialized = True

    def reload(self):
        """从文件重新加载设置数据到内存"""
        if os.path.exists(self._settings_file):
            with open(self._settings_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def save(self):
        """将当前内存中的设置数据保存到文件"""
        os.makedirs(os.path.dirname(self._settings_file), exist_ok=True)
        with open(self._settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def get_value(self, json_path, default=None):
        """
        使用glom根据JSON路径从数据中获取值

        Parameters:
            json_path (str): glom支持的JSON路径表达式。若为空，则将数据原样返回。
            default: 默认值，当路径不存在时返回

        Returns:
            路径对应的值
        """
        data = self.data

        if json_path:
            return glom(data, json_path, default=default)
        else:
            return data

    def set_value(self, json_path, value):
        """
        使用glom根据JSON路径设置值，自动创建中间缺失的字典层级。

        Parameters:
            json_path (str): glom支持的JSON路径表达式
            value: 要设置的值

        Examples:
        ```
            # 已有路径直接修改
            data = {"user": {"name": "Alice"}}
            self.set_value("user.name", "Bob")
            # data 现在为 {"user": {"name": "Bob"}}

            # 路径不存在时自动创建中间字典
            self.set_value("startup.exam_reminder.activated", True)
            # data 现在为 {"startup": {"exam_reminder": {"activated": True}}}
        ```
        """
        data = self.data

        if json_path:
            glom(data, Assign(json_path, value, missing=dict))
            self.data = data
        else:
            self.data = value