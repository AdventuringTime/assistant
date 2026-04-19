import pandas as pd
import json
import os
from datetime import datetime
import re

class RawDataProcessor:
    def __init__(self, raw_data_dir=None, output_dir=None):
        """
        初始化原始数据处理类
        
        Args:
            raw_data_dir: 原始Excel文件目录（默认：当前目录下的data/raw）
            output_dir: 输出JSON文件目录（默认：当前目录下的data）
        """
        # 设置默认路径为相对于当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        if raw_data_dir is None:
            self.raw_data_dir = os.path.join(current_dir, "data", "raw")
        else:
            self.raw_data_dir = raw_data_dir
            
        if output_dir is None:
            self.output_dir = os.path.join(current_dir, "data")
        else:
            self.output_dir = output_dir
        
    def read_excel_file(self, file_path):
        """
        读取Excel文件并返回DataFrame
        
        Args:
            file_path: Excel文件路径
            
        Returns:
            pandas.DataFrame: 读取的数据
        """
        # 读取"按时间"工作表
        df = pd.read_excel(file_path, sheet_name="按时间")
        return df
    
    def parse_time_format(self, time_str):
        """
        解析时间格式，转换为HH:MM格式
        
        Args:
            time_str: 时间字符串
            
        Returns:
            str: 格式化后的时间字符串
        """
        if pd.isna(time_str) or time_str == "" or time_str == "无":
            return None
            
        # 尝试不同的时间格式解析
        time_str = str(time_str).strip()
        
        if re.search(r'(\d{2}):(\d{2})', time_str):
            return time_str
        
        match = re.search(r'(\d{1,2})小时', time_str)
        if match:
            hours = int(match.group(1))
        else:
            hours = 0
        
        match = re.search(r'(\d{1,2})分钟', time_str)
        if match:
            minutes = int(match.group(1))
        else:
            minutes = 0

        assert hours > 0 or minutes > 0

        return f"{hours:02d}:{minutes:02d}"
        
        raise AssertionError(f"无法解析时间格式: {time_str}")
    
    def process_data(self, df):
        """
        处理数据并转换为JSON格式
        
        Args:
            df: 原始数据DataFrame
            
        Returns:
            dict: 处理后的数据字典
        """
        result = {}
        
        # 根据实际Excel表格结构设置列名
        date_col = "日期"
        start_col = "上班时间"
        end_col = "下班时间"
        rest_col = "休息时长"
        total_col = "合计工时"
        desc_col = "备注"
        
        # 处理每一行数据
        for index, row in df.iterrows():
            # 解析日期（格式：2026-04-01）
            date_value = row[date_col]
            assert not pd.isna(date_value) and str(date_value).strip() != ""
                
            # 从日期字符串中提取天数（格式：2026-04-01 -> 1）
            date_str = str(date_value).strip()
            date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
            assert date_match
                
            year = int(date_match.group(1))
            month = int(date_match.group(2))
            day = int(date_match.group(3))
            
            # 解析时间
            start_time = self.parse_time_format(row[start_col])
            end_time = self.parse_time_format(row[end_col])
            rest_time = self.parse_time_format(row[rest_col])
            total_work = self.parse_time_format(row[total_col])
            
            assert start_time and end_time
            
            # 构建记录
            record = {
                "from": start_time,
                "to": end_time,
                "total_work": total_work
            }
            
            # 添加休息时间
            if rest_time:
                record["rest"] = rest_time
            
            # 添加备注
            if desc_col and not pd.isna(row[desc_col]) and str(row[desc_col]).strip() != "":
                record["description"] = str(row[desc_col]).strip()
            
            # 添加到结果中（按日期分组）
            if str(day) not in result:
                result[str(day)] = []
            result[str(day)].append(record)
                
        return result, year, month
    
    def save_to_json(self, data, year, month, output_path=None):
        """
        将数据保存为JSON文件
        
        Args:
            data: 要保存的数据
            year: 年份
            month: 月份
            output_path: 输出文件路径
        """
        if not output_path:
            # 创建输出目录结构
            year_dir = os.path.join(self.output_dir, str(year)[-2:])  # 使用2位年份
            os.makedirs(year_dir, exist_ok=True)
            output_path = os.path.join(year_dir, f"{month}.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def process_all_files(self):
        """
        处理所有Excel文件
        """        
        # 获取所有Excel文件
        excel_files = []
        for file in os.listdir(self.raw_data_dir):
            if file.endswith(('.xlsx', '.xls')) and not file.startswith('~$'):
                excel_files.append(file)
        
        assert excel_files
        
        # 处理每个文件
        for file in excel_files:
            file_path = os.path.join(self.raw_data_dir, file)
            
            # 读取Excel文件
            df = self.read_excel_file(file_path)
            if df is None or df.empty:
                print(f"文件为空或读取失败: {file}")
                continue
            
            # 处理数据
            processed_data, year, month = self.process_data(df)
            
            if not processed_data:
                print(f"未处理出有效数据: {file}")
                continue
            
            # 保存为JSON
            self.save_to_json(processed_data, year, month)
            
            print(f"成功处理 {len(processed_data)} 天的数据")

def main():
    """主函数"""
    processor = RawDataProcessor()
    processor.process_all_files()

if __name__ == "__main__":
    main()