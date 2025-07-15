import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import os
from datetime import datetime
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings

# 忽略警告
warnings.filterwarnings('ignore')

# 配置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


class DalianWeatherAnalyzer:
    def __init__(self, data_path):
        """初始化分析器，加载并预处理数据"""
        self.df = self.load_data(data_path)
        self.preprocess_data()

    def load_data(self, data_path):
        """加载爬取的CSV数据"""
        try:
            df = pd.read_csv(data_path)
            print(f"成功加载数据: {data_path} (共 {len(df)} 条记录)")
            return df
        except Exception as e:
            print(f"数据加载失败: {str(e)}")
            raise

    def preprocess_data(self):
        """数据预处理：转换日期格式、提取年月、分类天气和风力"""
        # 转换日期为datetime格式
        self.df['日期'] = pd.to_datetime(self.df['日期'])
        self.df['年份'] = self.df['日期'].dt.year
        self.df['月份'] = self.df['日期'].dt.month

        # 筛选2022-2024年数据（分析用）和2025年1-6月数据（预测对比用）
        self.analysis_df = self.df[(self.df['年份'] >= 2022) & (self.df['年份'] <= 2024)]
        self.actual_2025 = self.df[(self.df['年份'] == 2025) & (self.df['月份'] <= 6)]

        # 天气状况分类（合并白天和夜晚，统一为晴/多云/阴/雨/雪）
        self.analysis_df['天气分类'] = self.analysis_df.apply(
            lambda x: self.classify_weather(x['白天天气'], x['夜晚天气']), axis=1
        )

        # 风力等级分类（合并白天和夜晚，统一为0级/1-2级/3-4级等）
        self.analysis_df['风力分类'] = self.analysis_df.apply(
            lambda x: self.classify_wind(x['白天风力'], x['夜晚风力']), axis=1
        )

    @staticmethod
    def classify_weather(day_weather, night_weather):
        """合并白天和夜晚天气，统一分类"""
        weather = f"{day_weather}|{night_weather}"
        if '晴' in weather:
            return '晴'
        elif '多云' in weather:
            return '多云'
        elif '阴' in weather:
            return '阴'
        elif '雨' in weather:  # 包含小雨、中雨等
            return '雨'
        elif '雪' in weather:  # 包含小雪、中雪等
            return '雪'
        else:
            return '其他'

    @staticmethod
    def classify_wind(day_wind, night_wind):
        """合并白天和夜晚风力，统一分类"""
        wind = f"{day_wind}|{night_wind}"
        if re.search(r'0级|无风|微风', wind):
            return '0级'
        elif re.search(r'1-2级|1级|2级', wind):
            return '1-2级'
        elif re.search(r'3-4级|3级|4级', wind):
            return '3-4级'
        elif re.search(r'5-6级|5级|6级', wind):
            return '5-6级'
        elif re.search(r'7-8级|7级|8级', wind):
            return '7-8级'
        else:
            return '9级以上'

    def plot_monthly_temp(self):
        """任务（2）：绘制近三年月平均气温变化图（取三年每月平均值）"""
        # 计算每月平均最高/最低温度（三年平均值）
        monthly_temp = self.analysis_df.groupby('月份').agg(
            平均最高温度=('最高温度', 'mean'),
            平均最低温度=('最低温度', 'mean')
        ).reset_index()

        # 绘制折线图
        plt.figure(figsize=(10, 6))
        plt.plot(monthly_temp['月份'], monthly_temp['平均最高温度'], 'r-', marker='o', label='平均最高温度')
        plt.plot(monthly_temp['月份'], monthly_temp['平均最低温度'], 'b-', marker='s', label='平均最低温度')

        plt.title('大连市2022-2024年月平均气温变化趋势', fontsize=14)
        plt.xlabel('月份', fontsize=12)
        plt.ylabel('温度(℃)', fontsize=12)
        plt.xticks(range(1, 13), [f'{i}月' for i in range(1, 13)])
        plt.grid(linestyle='--', alpha=0.7)
        plt.legend()
        plt.tight_layout()
        os.makedirs('output/figures', exist_ok=True)
        plt.savefig('output/figures/monthly_temp.png', dpi=300)
        print("已生成月平均气温变化图: output/figures/monthly_temp.png")

    def plot_wind_distribution(self):
        """任务（3）：绘制近三年风力情况分布图"""
        # 统计每月不同风力等级的天数
        wind_counts = self.analysis_df.groupby(['月份', '风力分类']).size().unstack(fill_value=0)
        # 按风力等级排序
        wind_order = ['0级', '1-2级', '3-4级', '5-6级', '7-8级', '9级以上']
        wind_counts = wind_counts.reindex(columns=wind_order)

        # 绘制堆叠柱状图
        plt.figure(figsize=(12, 6))
        wind_counts.plot(kind='bar', stacked=True, width=0.8, ax=plt.gca())

        plt.title('大连市2022-2024年每月风力等级分布', fontsize=14)
        plt.xlabel('月份', fontsize=12)
        plt.ylabel('天数', fontsize=12)
        plt.xticks(range(12), [f'{i}月' for i in range(1, 13)], rotation=0)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.legend(title='风力等级', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig('output/figures/wind_distribution.png', dpi=300)
        print("已生成风力情况分布图: output/figures/wind_distribution.png")

    def plot_weather_distribution(self):
        """任务（4）：绘制近三年天气状况分布图"""
        # 统计每月不同天气类型的天数
        weather_counts = self.analysis_df.groupby(['月份', '天气分类']).size().unstack(fill_value=0)
        # 按天气类型排序
        weather_order = ['晴', '多云', '阴', '雨', '雪', '其他']
        weather_counts = weather_counts.reindex(columns=weather_order)

        # 绘制堆叠柱状图
        plt.figure(figsize=(12, 6))
        weather_counts.plot(kind='bar', stacked=True, width=0.8, ax=plt.gca())

        plt.title('大连市2022-2024年每月天气状况分布', fontsize=14)
        plt.xlabel('月份', fontsize=12)
        plt.ylabel('天数', fontsize=12)
        plt.xticks(range(12), [f'{i}月' for i in range(1, 13)], rotation=0)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.legend(title='天气状况', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig('output/figures/weather_distribution.png', dpi=300)
        print("已生成天气状况分布图: output/figures/weather_distribution.png")

    def predict_and_visualize(self):
        """任务（5）：预测2025年1-6月平均最高温度，与实际值对比"""
        # 1. 准备训练数据：2022-2024年每月平均最高温度（取三年平均值）
        monthly_train = self.analysis_df.groupby(['年份', '月份'])['最高温度'].mean()
        monthly_avg = monthly_train.unstack('年份').mean(axis=1)  # 三年每月平均

        # 2. 训练SARIMA模型（考虑季节性，周期12个月）
        model = SARIMAX(monthly_avg, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        result = model.fit(disp=False)

        # 3. 预测2025年1-6月平均最高温度
        forecast = result.get_forecast(steps=6)
        pred_2025 = pd.DataFrame({
            '预测最高温度': forecast.predicted_mean,
            '月份': range(1, 7)
        })

        # 4. 整理2025年实际数据（每月平均最高温度）
        actual_monthly = self.actual_2025.groupby('月份')['最高温度'].mean().reset_index()

        # 5. 绘制预测vs实际对比折线图
        plt.figure(figsize=(10, 6))
        plt.plot(actual_monthly['月份'], actual_monthly['最高温度'], 'bo-', label='2025年实际值', markersize=8)
        plt.plot(pred_2025['月份'], pred_2025['预测最高温度'], 'ro--', label='预测值', markersize=8)

        plt.title('2025年1-6月平均最高温度预测 vs 实际', fontsize=14)
        plt.xlabel('月份', fontsize=12)
        plt.ylabel('平均最高温度(℃)', fontsize=12)
        plt.xticks(range(1, 7), [f'{i}月' for i in range(1, 7)])
        plt.grid(linestyle='--', alpha=0.7)
        plt.legend()
        plt.tight_layout()
        plt.savefig('output/figures/temp_prediction_2025.png', dpi=300)
        print("已生成预测与实际对比图: output/figures/temp_prediction_2025.png")

    def run_all_tasks(self):
        """执行所有分析任务"""
        print("\n开始执行数据分析任务...")
        self.plot_monthly_temp()          # 任务（2）
        self.plot_wind_distribution()    # 任务（3）
        self.plot_weather_distribution()  # 任务（4）
        self.predict_and_visualize()      # 任务（5）
        print("\n所有任务完成！图表已保存至 output/figures 目录")


if __name__ == "__main__":
    # 请替换为你的爬取数据CSV路径（例如：output/data/dalian_weather_2022-2025.csv）
    data_path = input("请输入爬取的天气数据CSV文件路径: ").strip()
    if not os.path.exists(data_path):
        print(f"错误：文件 {data_path} 不存在！")
    else:
        analyzer = DalianWeatherAnalyzer(data_path)
        analyzer.run_all_tasks()