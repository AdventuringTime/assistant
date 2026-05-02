import os


app_name = "探索酱的小助手"
icon_path = "assets/logo.ico"

# 注意：不要在全局常量中直接创建QIcon对象
# 因为QGuiApplication必须在QIcon之前创建
# 应该在应用程序启动后动态创建QIcon