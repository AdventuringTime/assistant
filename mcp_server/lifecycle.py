"""MCP 服务器生命周期管理，随主程序启动/停止

主程序（run.py）启动时调用 start()，退出时（aboutToQuit）调用 stop()。
服务器以 streamable HTTP 方式监听本机端口，供外部客户端连接。
"""

import os
import threading
import traceback


class McpServerManager:
    """MCP 服务器生命周期管理器（单例），在后台线程运行 streamable HTTP 服务器"""

    _instance = None
    _initialized = False

    HOST = "127.0.0.1"  # 仅本机可访问
    PORT = 8931         # 监听端口
    PATH = "/mcp"       # MCP 端点路径

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._thread = None
        self._uvicorn_server = None
        self._initialized = True

    def start(self):
        """启动 MCP 服务器后台线程（幂等）"""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="mcp-server", daemon=True)
        self._thread.start()

    def _run(self):
        """后台线程入口，创建事件循环并运行 streamable HTTP 服务器"""
        import asyncio
        import sys

        # pythonw（无控制台）环境下 sys.stdout/sys.stderr 为 None，
        # 会导致 uvicorn 日志配置时访问 isatty() 崩溃，这里用 devnull 替代
        if sys.stdout is None:
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        if sys.stderr is None:
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')

        import uvicorn

        from mcp_server.server import server

        try:
            app = server.streamable_http_app(streamable_http_path=self.PATH, host=self.HOST)
            config = uvicorn.Config(app, host=self.HOST, port=self.PORT, log_level="warning")
            self._uvicorn_server = uvicorn.Server(config)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._uvicorn_server.serve())
        except Exception:
            traceback.print_exc()

    def stop(self):
        """停止 MCP 服务器（幂等）"""
        if self._uvicorn_server is not None:
            self._uvicorn_server.should_exit = True
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3)
