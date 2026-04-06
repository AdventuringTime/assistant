import re
import traceback
import requests
from bs4 import BeautifulSoup
import json
import os
import webbrowser
from core.widgets import notification_system

from .utils.isFirstToday import is_first_run_today


# -------------------------- 配置参数 --------------------------
# 1. 目标网页及推送标题名称（若修改网页，需同时修改55行以正确定位新闻位置）
TARGETS = [
    ("https://gradschool.ustc.edu.cn/column/10", "研究生院新闻动态"),
    ("https://gradschool.ustc.edu.cn/column/9", "研究生院公告通知")
]
# 2. 检查间隔时间
CHECK_INTERVAL = 1800  # 检查间隔时间（秒）
FIRST_RUN_DELAY = 30  # 网络异常时重试时间（秒）
# 3. 存储文件路径
STORAGE_FILE = os.path.join(os.path.dirname(__file__), "data", "news_ids.json")
# 4. 新闻数量配置
MAX_NEWS_COUNT = 15  # 获取的新闻数量
CHECK_THRESHOLD = 10  # 检查更新的阈值
# --------------------------------------------------------------


def extract_news_id(url):
    """从新闻链接中提取最后一个斜杠后的数字ID（如从"/1958"提取"1958"）"""
    # 匹配最后一个斜杠后的数字序列（允许末尾有其他字符但取纯数字部分）
    match = re.search(r'/(\d+)[^/]*$', url)
    if match:
        return match.group(1)  # 返回提取的数字ID
    raise ValueError(f"无法从URL {url} 中提取数字ID")


def get_latest_news(target_url):
    """爬取目标网页，解析前MAX_NEWS_COUNT条新闻的链接并提取ID"""
    # 可添加浏览器 headers 避免反爬，添加header后在下一行get函数中同步添加headers=headers
    # headers = {
    #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0"
    # }
    response = requests.get(target_url, timeout=10)
    response.raise_for_status()  # 检查HTTP状态码，有异常则报错
    response.encoding = response.apparent_encoding  # 自动识别编码，避免乱码

    # 解析HTML，定位最新新闻链接
    soup = BeautifulSoup(response.text, "html.parser")
    # 提取前MAX_NEWS_COUNT条新闻的链接
    # 修改网页后请同时修改以下代码以正确定位新闻位置
    news_links = soup.find('div',class_="r-box").find('ul').\
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
    """打开指定的URL链接"""
    try:
        webbrowser.open(url)
    except:
        traceback.print_exc()

def check_news_update():
    """检查所有目标网页的新闻ID变化，有更新则推送通知"""
    global last_news_ids, network_error
    for i, (url, name) in enumerate(TARGETS):
        # 获取当前网页的最新ID和链接
        try:
            current_news_list = get_latest_news(url)
        except SystemExit: # 备调试使用
            quit()
        except requests.exceptions.RequestException:
            # 捕获网络请求异常
            traceback.print_exc()
            network_error = True  # 标记网络异常以后续调整等待时间
            continue
        except:
            traceback.print_exc()
            continue  # 获取失败则跳过该网页

        # 检查是否有新的新闻ID
        has_new_id = False
        first_new_news = None
        # 获取存储的所有历史ID
        stored_ids = last_news_ids[i]

        # 检查前CHECK_THRESHOLD条新闻中是否有新ID
        for news_id, news_title, news_link in current_news_list[:CHECK_THRESHOLD]:
            if news_id not in set(stored_ids):
                # 找到第一个未记载的ID
                first_new_news = (news_id, news_title, news_link)
                has_new_id = True
                break

        # 如果有新ID，推送通知
        if has_new_id and first_new_news:
            news_id, news_title, news_link = first_new_news
            # 推送系统通知
            notification_system.notify(
                title=name+"更新",
                content=news_title,
                click_action={"type": "open_url", "value": news_link}
            )

        # 更新记录的ID列表（只保留最新的MAX_NEWS_COUNT个）
        current_ids = [news[0] for news in current_news_list]
        if stored_ids != current_ids:  # 在ID列表发生变化时更新
            last_news_ids[i] = current_ids
            save_current_ids()

def load_saved_ids():
    """从JSON文件加载上次保存的新闻ID记录（直接返回列表形式）"""
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


if is_first_run_today():
    # 每天第一次运行时，打开所有目标网页
    for url, name in TARGETS:
        open_url(url)

# 存储每个网页的最新新闻ID
last_news_ids = load_saved_ids()