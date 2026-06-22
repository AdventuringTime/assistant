import re
import traceback
import requests
from bs4 import BeautifulSoup
import json
import os
import webbrowser
from homepage.widgets import NotificationSystemWidget

from core.functions import isnt_executed_today
from core.settings_manager import SettingsManager


# -------------------------- 配置参数 --------------------------
# 1. 目标网页及推送标题名称（若修改网页，需同时修改55行以正确定位新闻位置）
TARGETS = [
    ("https://gradschool.ustc.edu.cn/column/10", "研究生院新闻动态"),
    ("https://gradschool.ustc.edu.cn/column/9", "研究生院公告通知")
]
# 2. 检查间隔时间
news_monitor_settings = SettingsManager().get_value("startup.news_monitor")
CHECK_INTERVAL = news_monitor_settings["interval"]
DISCONNECT_DELAY = news_monitor_settings["disconnect_delay"]
# 3. 存储文件路径
STORAGE_FILE = os.path.join(os.path.dirname(__file__), "data", "news_ids.json")
# 4. 新闻数量配置
MAX_NEWS_COUNT = 15  # 获取的新闻数量
CHECK_THRESHOLD = 10  # 检查更新的阈值
# --------------------------------------------------------------

network_error = False


def extract_news_id(url):
    """
    从新闻链接中提取最后一个斜杠后的数字ID

    Parameters:
        url (str): 新闻链接

    Returns:
        str: 提取的数字ID

    Raises:
        ValueError: 无法从URL中提取数字ID时抛出
    """
    # 匹配最后一个斜杠后的数字序列（允许末尾有其他字符但取纯数字部分）
    match = re.search(r'/(\d+)[^/]*$', url)
    if match:
        return match.group(1)  # 返回提取的数字ID
    raise ValueError(f"无法从URL {url} 中提取数字ID")


def get_latest_news(target_url):
    """
    爬取目标网页，解析前MAX_NEWS_COUNT条新闻的链接并提取ID

    Parameters:
        target_url (str): 目标网页URL

    Returns:
        list: 新闻列表，每个元素为 (news_id, news_title, full_link)

    Raises:
        requests.exceptions.RequestException: 网络请求失败时抛出
        ValueError: 网页未找到新闻链接时抛出
    """
    response = requests.get(target_url, timeout=10)
    response.raise_for_status()  # 检查HTTP状态码，有异常则报错
    response.encoding = response.apparent_encoding  # 自动识别编码，避免乱码

    # 解析HTML，定位最新新闻链接
    soup = BeautifulSoup(response.text, "html.parser")
    # 提取前MAX_NEWS_COUNT条新闻的链接
    # 修改网页后请同时修改以下代码以正确定位新闻位置
    news_links = soup.find('div', class_="r-box").find('ul').\
        find_all('a', limit=MAX_NEWS_COUNT)
    if not news_links:
        raise ValueError(f"网页 {target_url} 未找到新闻链接")

    news_list = []
    for link in news_links:
        # 获取完整链接（处理相对路径）
        link_href = link.get('href')
        full_link = link_href if link_href.startswith("http") else f"https://gradschool.ustc.edu.cn{link_href}"

        # 直接使用链接作为新闻ID
        news_id = link_href

        # 提取新闻标题
        try:
            news_title = link.get_text(strip=True)
        except:
            news_title = "未知标题"

        news_list.append((news_id, news_title, full_link))

    return news_list


def open_url(url):
    """
    打开指定的URL链接

    Parameters:
        url (str): 要打开的URL链接
    """
    try:
        webbrowser.open(url)
    except:
        traceback.print_exc()

def check_news_update():
    """
    检查所有目标网页的新闻ID变化，有更新则推送通知。返回新的检查间隔时间（秒）

    遍历所有目标网页，获取最新新闻列表，与存储的历史ID对比，
    如果发现新新闻则推送通知，并更新存储的ID记录。

    Returns:
        int: 下次检查的间隔时间（秒），网络异常时返回DISCONNECT_DELAY，
             正常情况返回CHECK_INTERVAL
    """
    global last_news_ids, network_error
    for i, (url, name) in enumerate(TARGETS):
        # 获取当前网页的最新ID和链接
        try:
            current_news_list = get_latest_news(url)
        except SystemExit:  # 备调试使用
            quit()
        except requests.exceptions.RequestException:
            # 捕获网络请求异常
            traceback.print_exc()
            network_error = True  # 标记网络异常以后续调整等待时间
            continue
        except:
            traceback.print_exc()
            continue  # 获取失败则跳过该网页

        # 获取存储的所有历史ID
        stored_ids = last_news_ids[i]

        # 检查前CHECK_THRESHOLD条新闻中是否有新ID
        for news_id, news_title, news_link in current_news_list[:CHECK_THRESHOLD]:
            if news_id not in set(stored_ids):
                # 找到所有未记载的ID，推送系统通知
                NotificationSystemWidget().notify(
                    title=name + "更新",
                    content=news_title,
                    click_action={"type": "open_url", "value": url}  # 打开主界面
                )

        # 更新记录的ID列表（只保留最新的MAX_NEWS_COUNT个）
        current_ids = [news[0] for news in current_news_list]
        if stored_ids != current_ids:  # 在ID列表发生变化时更新
            last_news_ids[i] = current_ids
            save_current_ids()

    if network_error:
        return DISCONNECT_DELAY  # 网络异常时返回延迟时间
    else:
        return CHECK_INTERVAL  # 正常情况返回默认间隔时间

def load_saved_ids():
    """
    从JSON文件加载上次保存的新闻ID记录（直接返回列表形式）

    Returns:
        list: 新闻ID列表，每个目标网页对应一个子列表
    """
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)  # 直接返回列表
        except (json.JSONDecodeError, IOError) as e:
            pass
    return [[None]] * len(TARGETS)  # 首次运行或文件损坏时返回默认值

def save_current_ids():
    """将当前最新的ID记录（列表形式）保存到JSON文件"""
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(last_news_ids, f, ensure_ascii=False, indent=4)


if isnt_executed_today(os.path.join(os.path.dirname(__file__), "data", "last_run_date.json")):
    # 每天第一次运行时，打开所有目标网页
    for url, name in TARGETS:
        NotificationSystemWidget().notify(
            title=name,
            content="检查一下哦",
            click_action={"type": "open_url", "value": url} # 打开主界面
        )

# 存储每个网页的最新新闻ID
last_news_ids = load_saved_ids()