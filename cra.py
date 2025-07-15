import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
import os
from datetime import datetime
from fake_useragent import UserAgent
import warnings

# 忽略警告
warnings.filterwarnings('ignore')


class WeatherSpider:
    """天气数据爬虫类"""

    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.retry_count = 3  # 重试次数
        self.delay_range = (1, 3)  # 随机延迟范围（秒）
        self.base_url = "https://www.tianqihoubao.com"  # 天气后报网站基础URL

    def get_headers(self):
        """生成随机的请求头"""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": self.base_url,
            "Upgrade-Insecure-Requests": "1"
        }

    def get_month_urls(self, city_code="dalian", start_year=2021, end_year=2023):
        """生成所有需要爬取的月份URL

        Args:
            city_code: 城市代码，例如"dalian"代表大连
            start_year: 开始年份
            end_year: 结束年份

        Returns:
            包含年份、月份和URL的元组列表
        """
        urls = []
        current_year = datetime.now().year
        current_month = datetime.now().month

        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                # 跳过未来月份
                if year > current_year or (year == current_year and month > current_month):
                    continue
                url = f"{self.base_url}/lishi/{city_code}/month/{year}{month:02d}.html"
                urls.append((year, month, url))
        return urls

    def parse_weather_data(self, html):
        """解析天气数据

        Args:
            html: 网页HTML内容

        Returns:
            解析后的天气数据列表
        """
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='weather-table')
        if not table:
            print("未找到天气表格")
            return []

        data = []
        rows = table.find_all('tr')[1:]  # 跳过表头

        for row in rows:
            # 跳过空行和分隔行
            if not row.find_all('td') or row.find('hr'):
                continue

            cols = row.find_all('td')
            if len(cols) < 4:
                continue

            # 解析日期
            date_link = cols[0].find('a')
            date_text = date_link.get_text(strip=True) if date_link else cols[0].get_text(strip=True)

            # 更健壮的日期解析
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
            if not date_match:
                continue

            try:
                date = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
            except:
                continue

            # 解析温度
            temp_text = cols[2].get_text(strip=True)
            temps = re.findall(r'-?\d+', temp_text)

            try:
                high_temp = int(temps[0]) if len(temps) > 0 else None
                low_temp = int(temps[1]) if len(temps) > 1 else None
            except (ValueError, IndexError):
                high_temp = low_temp = None

            # 解析天气状况
            weather_text = cols[1].get_text(strip=True).replace('\xa0', ' ')  # 处理特殊空格
            weather_parts = weather_text.split('/')
            day_weather = weather_parts[0].strip() if len(weather_parts) > 0 else ''
            night_weather = weather_parts[1].strip() if len(weather_parts) > 1 else day_weather

            # 解析风力
            wind_text = cols[3].get_text(strip=True).replace('\xa0', ' ')  # 处理特殊空格
            wind_parts = wind_text.split('/')
            day_wind = wind_parts[0].strip() if len(wind_parts) > 0 else ''
            night_wind = wind_parts[1].strip() if len(wind_parts) > 1 else day_wind

            data.append({
                '日期': date,
                '最高温度': high_temp,
                '最低温度': low_temp,
                '白天天气': day_weather,
                '夜晚天气': night_weather,
                '白天风力': day_wind,
                '夜晚风力': night_wind
            })

        return data

    def fetch_month_data(self, year, month, url):
        """获取单个月份的数据（带重试机制）

        Args:
            year: 年份
            month: 月份
            url: 要爬取的URL

        Returns:
            解析后的天气数据列表
        """
        for attempt in range(self.retry_count):
            try:
                # 随机延迟避免被封
                delay = random.uniform(*self.delay_range)
                time.sleep(delay)

                print(f"正在爬取 {year}年{month}月 数据...")
                headers = self.get_headers()
                response = self.session.get(url, headers=headers, timeout=15)

                # 检查响应状态
                if response.status_code != 200:
                    print(f"请求失败，状态码: {response.status_code}, 尝试 {attempt + 1}/{self.retry_count}")
                    continue

                # 尝试多种编码
                for encoding in ['gbk', 'gb18030', 'utf-8']:
                    try:
                        response.encoding = encoding
                        month_data = self.parse_weather_data(response.text)
                        if month_data:
                            print(f"成功爬取 {year}年{month}月 {len(month_data)} 条记录")
                            return month_data
                    except Exception as e:
                        print(f"编码 {encoding} 解析失败: {str(e)}")

                print(f"所有编码尝试失败，跳过 {year}年{month}月")
                return []

            except requests.exceptions.RequestException as e:
                print(f"网络错误: {str(e)}, 尝试 {attempt + 1}/{self.retry_count}")
            except Exception as e:
                print(f"解析错误: {str(e)}, 尝试 {attempt + 1}/{self.retry_count}")

        print(f"爬取 {year}年{month}月 数据失败，跳过")
        return []

    def crawl_weather_data(self, city_code="dalian", start_year=2021, end_year=2023):
        """爬取多年的天气数据

        Args:
            city_code: 城市代码
            start_year: 开始年份
            end_year: 结束年份

        Returns:
            包含所有天气数据的DataFrame
        """
        urls = self.get_month_urls(city_code, start_year, end_year)
        print(f"准备爬取 {len(urls)} 个月份的数据...")

        all_data = []
        success_count = 0
        fail_count = 0

        # 使用多线程加速爬取
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as executor:  # 减少工作线程数避免被封
            futures = []
            for year, month, url in urls:
                futures.append(executor.submit(self.fetch_month_data, year, month, url))

            for future in futures:
                month_data = future.result()
                if month_data:
                    all_data.extend(month_data)
                    success_count += 1
                else:
                    fail_count += 1

        print(f"爬取完成: 成功 {success_count} 个月份, 失败 {fail_count} 个月份")

        # 转换为DataFrame并排序
        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame(all_data)
        df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
        df = df.dropna(subset=['日期'])
        df = df.sort_values('日期')
        df['日期'] = df['日期'].dt.strftime('%Y-%m-%d')

        return df


def main():
    print("=" * 50)
    print("中国城市天气数据爬取程序")
    print("=" * 50)

    # 获取用户输入
    city_code = input("请输入要爬取的城市代码 (例如: dalian 代表大连): ").strip() or "dalian"
    start_year = int(input("请输入开始年份 (例如: 2021): ") or 2021)
    end_year = int(input("请输入结束年份 (例如: 2023): ") or 2023)

    # 确保年份范围合理
    current_year = datetime.now().year
    start_year = max(2010, min(start_year, current_year))
    end_year = max(start_year, min(end_year, current_year))

    print(f"\n将爬取 {city_code} 市 {start_year}-{end_year} 年的天气数据")

    # 创建爬虫实例
    spider = WeatherSpider()

    # 开始爬取数据
    print("\n开始爬取天气数据...")
    start_time = time.time()

    weather_data = spider.crawl_weather_data(city_code, start_year, end_year)

    if weather_data.empty:
        print("\n⚠️ 警告: 未能获取有效数据，程序终止")
        return

    # 确保目录存在
    os.makedirs('output/data', exist_ok=True)

    # 保存原始数据
    output_file = f'output/data/{city_code}_weather_{start_year}-{end_year}.csv'
    weather_data.to_csv(output_file, index=False, encoding='utf_8_sig')

    elapsed = time.time() - start_time
    print(f"\n数据爬取完成! 总耗时: {elapsed:.2f} 秒")
    print(f"数据已保存至: {output_file} ({len(weather_data)} 条记录)")

    # 显示数据示例
    print("\n数据示例:")
    print(weather_data.head())


if __name__ == "__main__":
    main()