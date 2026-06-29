"""
日程数据存储格式迁移脚本

将旧的按日存储格式迁移为按月存储格式。

旧格式: data/{year}/{month}/{day}.json  （每个文件存一天的日程）
新格式: data/{year}-{month:02d}.json    （每个文件存一个月的日程）

使用方法：
    更新版本后首次运行前，在终端中执行：
    python apps/calendar/migrate_to_monthly.py

注意：
    - 此脚本会读取旧格式目录中的所有日程文件，合并写入月度文件。
    - 迁移完成后会自动删除旧的年份/月份目录结构。
    - 如果已经是新格式（无旧目录结构），脚本会提示无需迁移并退出。
"""

import json
import os
import shutil
import sys

# 确保可以从项目根目录导入
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

DATA_DIR = os.path.join(_project_root, "apps/calendar/data")


def month_file_path(year, month):
    """
    获取月度文件的路径

    Parameters:
        year (int): 年份
        month (int): 月份（1-12）

    Returns:
        str: 月度文件路径
    """
    return os.path.join(DATA_DIR, f"{year}-{month:02d}.json")


def has_old_format():
    """
    检查是否存在旧格式的目录结构

    旧格式的特征是 data 目录下存在以年份命名的子目录。

    Returns:
        bool: 是否存在旧格式数据
    """
    if not os.path.exists(DATA_DIR):
        return False
    for name in os.listdir(DATA_DIR):
        if os.path.isdir(os.path.join(DATA_DIR, name)) and name.isdigit():
            return True
    return False


def migrate():
    """
    执行数据迁移：将旧格式按月合并为新格式

    遍历所有年份/月份目录，读取每天的日程文件，
    合并写入月度 JSON 文件，然后删除旧目录。
    """
    if not os.path.exists(DATA_DIR):
        print(f"数据目录不存在: {DATA_DIR}")
        print("无需迁移。")
        return

    if not has_old_format():
        print("未检测到旧格式目录结构，数据已经是按月存储格式，无需迁移。")
        return

    total_days = 0
    total_months = 0
    migrated_months = []

    # 遍历年份目录
    for name in sorted(os.listdir(DATA_DIR)):
        year_path = os.path.join(DATA_DIR, name)
        if not os.path.isdir(year_path) or not name.isdigit():
            continue

        year = int(name)

        # 遍历月份目录
        for month_name in sorted(os.listdir(year_path), key=int):
            month_path = os.path.join(year_path, month_name)
            if not os.path.isdir(month_path) or not month_name.isdigit():
                continue

            month = int(month_name)
            monthly_data = {}
            month_day_count = 0

            # 遍历该月所有日程文件
            for day_file in sorted(os.listdir(month_path), key=lambda x: x.replace('.json', '')):
                if not day_file.endswith('.json'):
                    continue
                day = day_file[:-5]  # 去掉 .json 后缀
                file_path = os.path.join(month_path, day_file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        day_schedules = json.load(f)
                    if day_schedules:
                        monthly_data[day] = day_schedules
                        month_day_count += 1
                except (json.JSONDecodeError, OSError) as e:
                    print(f"  警告: 无法读取 {file_path}: {e}")
                    continue

            # 写入月度文件
            if monthly_data:
                new_file_path = month_file_path(year, month)
                os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
                with open(new_file_path, 'w', encoding='utf-8') as f:
                    json.dump(monthly_data, f, ensure_ascii=False, indent=4)
                total_days += month_day_count
                total_months += 1
                migrated_months.append(f"{year}-{month:02d} ({month_day_count}天)")
                print(f"  ✓ {year}-{month:02d}: 合并 {month_day_count} 天日程 -> {new_file_path}")
            else:
                print(f"  - {year}-{month:02d}: 目录为空，跳过")

        # 删除旧年份目录
        shutil.rmtree(year_path)
        print(f"  🗑 已删除旧目录: {year_path}")

    print(f"\n迁移完成！共处理 {total_months} 个月、{total_days} 天的日程数据。")
    if migrated_months:
        print("已迁移的月份:")
        for m in migrated_months:
            print(f"  - {m}")


def main():
    """主入口"""
    print("=" * 50)
    print("  日程数据存储格式迁移工具")
    print("  旧格式: data/{year}/{month}/{day}.json")
    print("  新格式: data/{year}-{month:02d}.json")
    print("=" * 50)
    print()

    if not os.path.exists(DATA_DIR):
        print(f"数据目录不存在: {DATA_DIR}")
        print("请确认项目路径正确。")
        sys.exit(1)

    if not has_old_format():
        print("✅ 未检测到旧格式目录结构，数据已经是按月存储格式，无需迁移。")
        sys.exit(0)

    print(f"数据目录: {DATA_DIR}")
    print()

    # 列出旧格式目录结构
    print("检测到旧格式目录结构:")
    for name in sorted(os.listdir(DATA_DIR)):
        year_path = os.path.join(DATA_DIR, name)
        if os.path.isdir(year_path) and name.isdigit():
            months = [m for m in os.listdir(year_path)
                      if os.path.isdir(os.path.join(year_path, m)) and m.isdigit()]
            for month in sorted(months, key=int):
                month_path = os.path.join(year_path, month)
                day_count = len([f for f in os.listdir(month_path) if f.endswith('.json')])
                print(f"  {name}年{month}月: {day_count} 天")
    print()

    # 执行迁移
    migrate()
    print("\n请现在运行主程序，日程管理器将使用新的月度文件格式。")


if __name__ == "__main__":
    main()