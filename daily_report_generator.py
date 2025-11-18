import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.table import Table
import numpy as np
from datetime import datetime, timedelta
import os
import calendar

class DailyReportGenerator:
    def __init__(self):
        """初始化日报生成器"""
        self._setup_font()
        self._define_columns()
        
    def _setup_font(self):
        """设置中文字体"""
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    
    def _define_columns(self):
        """定义列名映射和处理规则"""
        self.numeric_columns = [
            '注册用户', '完成KYC用户', '邀请用户', 'B端邀请用户', '直客人数',
            'FTD', 'FTT', 'effective FTT',
            '充值人数', '充值折U', '提现人数', '提现折U', '净充值折U',
            '合约划出', '合约划入', '合约净划入', '赠金划出', '赠金划入', '合约赠金净划入',
            '合约交易次数', '合约交易人数', '合约交易金额', '合约交易手续费', '合约交易平仓盈亏', '合约赠金手续费',
            '现货交易次数', '现货交易人数', '现货交易金额', '现货交易手续费', '赠金真实消耗',
            'B端返佣', 'B端合约返佣', 'B端现货返佣', 'C端返佣', 'C端合约返佣', 'C端现货返佣',
            '净手续费(现货&合约)', '手续费(现货&合约)', '交易人数',
            '首次合约赠金交易人数', '合约赠金亏损', 'effective FTTf', 
            '次日留存合约新增交易用户数', 'EFTT(充值≥100U)', 'EFTTC'
        ]
        
        self.column_mapping = {
            'dimension': 'Dimension',
            '统计日期': 'Date',
            '注册用户': 'Reg',
            'FTD': 'FTD',
            'FTT': 'FTT',
            '充值折U': 'Deposit ($)',
            '提现折U': 'Withdraw ($)',
            '净充值折U': 'Net Deposit ($)',
            '交易人数': 'DAU',
            '现货交易金额': 'Spot Vol ($)',
            '现货交易手续费': 'Spot Fee ($)',
            '合约交易金额': 'Futures Vol ($)',
            '合约交易手续费': 'Futures Fee ($)',
            '总交易额': 'Total Vol ($)',
            '手续费(现货&合约)': 'Total Fee ($)',
            '净手续费(现货&合约)': 'Profit Fee ($)',
            'effective FTT': 'EFTT',
            'EFTTC': 'EFTTC',
            '赠金真实消耗': 'Bonus Consumption',
            '合约赠金净划入': 'Bonus Transfer Into',
            '合约交易平仓盈亏': 'Futures PNL'
        }
        
        self.int_columns = ['Reg', 'FTD', 'FTT', 'DAU', 'Activate KOL', 'EFTTC']
        
        self.display_columns = [
            'Date', 'Reg', 'FTD', 'FTT', 'Deposit ($)', 'Withdraw ($)', 
            'Net Deposit ($)', 'DAU', 'Spot Vol ($)', 'Spot Fee ($)', 
            'Futures Vol ($)', 'Futures Fee ($)', 'Total Vol ($)', 'Total Fee ($)',
            'Profit Fee ($)', 'Activate KOL', 'EFTTC', 'Bonus Consumption', 
            'Bonus Transfer Into', 'Futures PNL'
        ]
    
    def format_number(self, value):
        """格式化数字显示"""
        if pd.isna(value) or value == 0:
            return '0'
        elif abs(value) >= 1000000:
            return f'{value:,.0f}'
        elif abs(value) >= 1000:
            return f'{value:,.0f}'
        elif isinstance(value, int) or value == int(value):
            return f'{int(value)}'
        else:
            return f'{value:,.0f}' if abs(value) >= 10 else f'{value:.1f}'
    
    def is_month_complete(self, month_data, year, month):
        """判断某月数据是否完整"""
        days_in_month = calendar.monthrange(year, month)[1]
        unique_days = month_data['Date_dt'].dt.day.nunique()
        return unique_days >= days_in_month
    
    def process_raw_data(self, df):
        """处理原始数据"""
        # 清理数值列
        for col in self.numeric_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '').replace('nan', '0')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 填充其他列的NaN值
        df = df.fillna('')
        
        # 创建维度
        df['商务总监'] = df['商务总监'].astype(str).replace('nan', '').replace('0', '')
        df['商务BD'] = df['商务BD'].astype(str).replace('nan', '').replace('0', '')
        df['dimension'] = df['商务总监'] + ' - ' + df['商务BD']
        df['dimension'] = df['dimension'].str.strip().str.replace(' -  - ', ' - ')
        df['dimension'] = df['dimension'].str.replace('^ - ', '', regex=True)
        df['dimension'] = df['dimension'].str.replace(' - $', '', regex=True)
        
        # 过滤离职记录
        original_count = len(df)
        df = df[~df['商务总监'].str.contains('离职', na=False)].copy()
        df = df[~df['商务BD'].str.contains('离职', na=False)].copy()
        df = df[~df['dimension'].str.contains('离职', na=False)].copy()
        filtered_count = original_count - len(df)
        
        if filtered_count > 0:
            print(f"已过滤 {filtered_count} 条包含'离职'的记录")
        
        return df
    
    def _aggregate_data_impl(self, df, groupby_cols, include_kol_count=True):
        """聚合数据的内部实现"""
        # 按指定列分组汇总
        result = df.groupby(groupby_cols).agg({
            '注册用户': 'sum',
            'FTD': 'sum',
            'FTT': 'sum',
            '充值折U': 'sum',
            '提现折U': 'sum',
            '净充值折U': 'sum',
            '交易人数': 'sum',
            '现货交易金额': 'sum',
            '现货交易手续费': 'sum',
            '合约交易金额': 'sum',
            '合约交易手续费': 'sum',
            '手续费(现货&合约)': 'sum',
            '净手续费(现货&合约)': 'sum',
            'effective FTT': 'sum',
            'EFTTC': 'sum',
            '赠金真实消耗': 'sum',
            '合约赠金净划入': 'sum',
            '合约交易平仓盈亏': 'sum',
        }).reset_index()
        
        # 计算总交易量
        result['总交易额'] = result['现货交易金额'] + result['合约交易金额']
        
        # 计算Activate KOL（如果需要）
        if include_kol_count and 'dimension' in groupby_cols:
            kol_groupby = ['dimension', '统计日期']
            kol_counts = df.groupby(kol_groupby)['总代理'].nunique().reset_index()
            kol_counts.columns = kol_groupby + ['Activate KOL']
            result = result.merge(kol_counts, on=kol_groupby, how='left')
            result['Activate KOL'] = result['Activate KOL'].fillna(0)
        
        # 重命名列
        result = result.rename(columns=self.column_mapping)
        
        # 转换数据类型
        for col in self.int_columns:
            if col in result.columns:
                result[col] = result[col].astype(int)
        
        # 四舍五入浮点数列
        exclude_cols = ['Date', 'Dimension'] + self.int_columns
        if '总代理' in result.columns:
            exclude_cols.append('总代理')
        float_columns = [col for col in result.columns if col not in exclude_cols]
        for col in float_columns:
            result[col] = result[col].round(2)
        
        return result
    
    def aggregate_data(self, df):
        """按维度和日期聚合数据"""
        return self._aggregate_data_impl(df, ['dimension', '统计日期'], include_kol_count=True)
    
    def aggregate_data_by_kol(self, df):
        """按总代理、维度和日期聚合数据"""
        # 过滤掉总代理为空的记录
        df_kol = df[df['总代理'].notna() & (df['总代理'] != '')].copy()
        
        if len(df_kol) == 0:
            return pd.DataFrame()
        
        return self._aggregate_data_impl(df_kol, ['总代理', 'dimension', '统计日期'], include_kol_count=False)
    
    def create_table_data(self, agent_data, kol_name=None):
        """为单个代理创建表格数据
        
        Args:
            agent_data: 代理数据
            kol_name: 总代理名称（如果为总代理数据）
        """
        # 转换日期列为datetime
        agent_data['Date_dt'] = pd.to_datetime(agent_data['Date'], errors='coerce')
        agent_data = agent_data[agent_data['Date_dt'].notna()].copy()
        
        if len(agent_data) == 0:
            return None, None, None, None
        
        # 按日期倒序排列
        agent_data = agent_data.sort_values('Date_dt', ascending=False).reset_index(drop=True)
        
        # 添加年月信息
        agent_data['Year'] = agent_data['Date_dt'].dt.year
        agent_data['Month'] = agent_data['Date_dt'].dt.month
        agent_data['YearMonth'] = agent_data['Date_dt'].dt.to_period('M')
        
        # 获取最新的年月
        latest_year_month = agent_data['YearMonth'].iloc[0]
        
        # 提取商务名称
        if kol_name:
            # 总代理数据
            business_name = kol_name
            if ' - ' in agent_data['Dimension'].iloc[0]:
                parts = agent_data['Dimension'].iloc[0].split(' - ')
                supervisor = parts[0].strip()
                bd_name = parts[-1].strip()
            else:
                supervisor = ''
                bd_name = agent_data['Dimension'].iloc[0]
        else:
            # 普通代理数据
            if ' - ' in agent_data['Dimension'].iloc[0]:
                parts = agent_data['Dimension'].iloc[0].split(' - ')
                supervisor = parts[0].strip()
                business_name = parts[-1].strip()
            else:
                supervisor = ''
                business_name = agent_data['Dimension'].iloc[0]
            bd_name = business_name
        
        # 只保留存在的列
        available_columns = [col for col in self.display_columns if col in agent_data.columns]
        
        # 按月份分组构建表格数据
        table_data = []
        month_groups = agent_data.groupby('YearMonth', sort=False)
        
        for idx, (year_month, month_data) in enumerate(month_groups):
            year = month_data['Year'].iloc[0]
            month = month_data['Month'].iloc[0]
            is_latest_month = (year_month == latest_year_month)
            is_complete = self.is_month_complete(month_data, year, month)
            
            if is_latest_month:
                # 最新月份：显示每日数据 + 该月总和
                for _, row in month_data.iterrows():
                    formatted_row = []
                    for col in available_columns:
                        value = row[col]
                        if col == 'Date':
                            date_str = row['Date_dt'].strftime('%Y-%m-%d')
                            formatted_row.append(date_str)
                        else:
                            formatted_row.append(self.format_number(value))
                    table_data.append(formatted_row)
                
                # 添加最新月的总和行
                self._add_month_total_row(table_data, month_data, available_columns, year, month)
                
            elif is_complete:
                # 历史完整月份：只显示该月总和
                self._add_month_total_row(table_data, month_data, available_columns, year, month)
        
        # 添加TOTAL行
        if len(agent_data) > 0:
            self._add_total_row(table_data, agent_data, available_columns)
        
        return table_data, available_columns, business_name, supervisor
    
    def _add_month_total_row(self, table_data, month_data, available_columns, year, month):
        """添加月度汇总行"""
        month_total_label = f"{year}/{month:02d}"
        month_total_row = [month_total_label]
        for col in available_columns[1:]:
            if col in ['DAU', 'Activate KOL']:
                month_total_row.append(self.format_number(month_data[col].max()))
            else:
                month_total_row.append(self.format_number(month_data[col].sum()))
        table_data.append(month_total_row)
    
    def _add_total_row(self, table_data, agent_data, available_columns):
        """添加总计行"""
        total_row = ['TOTAL']
        for col in available_columns[1:]:
            if col in ['DAU', 'Activate KOL']:
                total_row.append(self.format_number(agent_data[col].max()))
            else:
                total_row.append(self.format_number(agent_data[col].sum()))
        table_data.append(total_row)
    
    def create_visualization(self, table_data, available_columns, business_name, supervisor):
        """创建可视化图表"""
        fig_height = max(len(table_data) * 0.4 + 3, 11)
        fig, ax = plt.subplots(figsize=(24, fig_height))
        ax.axis('tight')
        ax.axis('off')
        
        # 创建表格
        table = ax.table(
            cellText=table_data,
            colLabels=available_columns,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 0.92]
        )
        
        # 设置表格样式
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        
        # 识别月总和行
        month_summary_rows = []
        for i, row_data in enumerate(table_data):
            if len(row_data[0]) == 7 and '/' in row_data[0] and row_data[0] != 'TOTAL':
                month_summary_rows.append(i + 1)
        
        # 设置单元格样式
        self._apply_table_styles(table, table_data, available_columns, month_summary_rows)
        
        # 添加标题
        fig.text(0.05, 0.98, business_name, 
                fontsize=22, fontweight='bold', 
                verticalalignment='top',
                color='#2c3e50')
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.96, bottom=0.02)
        
        return fig
    
    def _apply_table_styles(self, table, table_data, available_columns, month_summary_rows):
        """应用表格样式"""
        # 表头样式
        for i in range(len(available_columns)):
            cell = table[(0, i)]
            cell.set_facecolor('#3d3d3d')
            cell.set_text_props(weight='bold', color='white', fontsize=9, ha='center')
            cell.set_height(0.08)
            cell.set_edgecolor('white')
            cell.set_linewidth(1.5)
        
        # 数据行样式
        row_counter = 0
        for i in range(1, len(table_data) + 1):
            for j in range(len(available_columns)):
                cell = table[(i, j)]
                
                is_month_summary = i in month_summary_rows
                is_total = 'TOTAL' in str(table_data[i-1][0])
                
                if is_total:
                    self._style_total_cell(cell)
                elif is_month_summary:
                    self._style_month_summary_cell(cell)
                    row_counter = 0
                else:
                    self._style_data_cell(cell, row_counter % 2 == 0)
                    
                if not is_month_summary and not is_total and j == len(available_columns) - 1:
                    row_counter += 1
    
    def _style_total_cell(self, cell):
        """设置总计行样式"""
        cell.set_facecolor('#3d3d3d')
        cell.set_text_props(weight='bold', color='white', fontsize=10, ha='center')
        cell.set_height(0.07)
        cell.set_edgecolor('white')
        cell.set_linewidth(1.5)
    
    def _style_month_summary_cell(self, cell):
        """设置月度汇总行样式"""
        cell.set_facecolor('#f9a825')
        cell.set_text_props(weight='bold', color='white', fontsize=10, ha='center')
        cell.set_height(0.07)
        cell.set_edgecolor('white')
        cell.set_linewidth(1.5)
    
    def _style_data_cell(self, cell, is_even_row):
        """设置数据行样式"""
        cell.set_facecolor('#f8f9fa' if is_even_row else 'white')
        cell.set_text_props(fontsize=9, ha='center')
        cell.set_height(0.06)
        cell.set_edgecolor('#e0e0e0')
        cell.set_linewidth(0.5)
    
    def save_report(self, fig, business_name, supervisor, output_dir='bd_reports'):
        """保存报告图片"""
        os.makedirs(output_dir, exist_ok=True)
        
        if supervisor:
            supervisor_folder = os.path.join(output_dir, supervisor.replace('/', '_').replace('\\', '_'))
            os.makedirs(supervisor_folder, exist_ok=True)
            safe_name = business_name.replace('/', '_').replace('\\', '_').replace(' ', '_')
            output_path = os.path.join(supervisor_folder, f'{safe_name}_report.png')
        else:
            safe_name = business_name.replace('/', '_').replace('\\', '_').replace(' ', '_')
            output_path = os.path.join(output_dir, f'{safe_name}_report.png')
        
        fig.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        
        return output_path
    
    def save_kol_report(self, fig, kol_name, supervisor, bd_name, output_dir='agent_reports'):
        """保存总代理报告图片到指定路径结构"""
        # 创建路径结构: agent_reports/总监名文件夹/BD名文件夹/具体总代数据
        safe_supervisor = supervisor.replace('/', '_').replace('\\', '_')
        safe_bd_name = bd_name.replace('/', '_').replace('\\', '_')
        safe_kol_name = kol_name.replace('/', '_').replace('\\', '_').replace(' ', '_')

        # 构建完整路径
        kol_folder = os.path.join(output_dir, safe_supervisor, safe_bd_name)
        os.makedirs(kol_folder, exist_ok=True)

        output_path = os.path.join(kol_folder, f'{safe_kol_name}_report.png')

        fig.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        return output_path
    
    def create_supervisor_report(self, supervisor_name, supervisor_data, output_dir='supervisor_reports'):
        """为单个总监创建团队报表（包含该总监下所有商务BD）"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 转换日期
        supervisor_data['Date_dt'] = pd.to_datetime(supervisor_data['Date'], errors='coerce')
        supervisor_data = supervisor_data[supervisor_data['Date_dt'].notna()].copy()
        
        if len(supervisor_data) == 0:
            print(f"⚠ {supervisor_name}: 没有有效日期数据，跳过")
            return None
        
        # 按日期倒序
        supervisor_data = supervisor_data.sort_values('Date_dt', ascending=False).reset_index(drop=True)
        
        # 添加年月信息
        supervisor_data['Year'] = supervisor_data['Date_dt'].dt.year
        supervisor_data['Month'] = supervisor_data['Date_dt'].dt.month
        supervisor_data['YearMonth'] = supervisor_data['Date_dt'].dt.to_period('M')
        
        # 按日期汇总所有商务的数据
        daily_totals = supervisor_data.groupby(['Date', 'Date_dt', 'Year', 'Month', 'YearMonth']).agg({
            'Reg': 'sum',
            'FTD': 'sum',
            'FTT': 'sum',
            'Deposit ($)': 'sum',
            'Withdraw ($)': 'sum',
            'Net Deposit ($)': 'sum',
            'DAU': 'sum',
            'Spot Vol ($)': 'sum',
            'Spot Fee ($)': 'sum',
            'Futures Vol ($)': 'sum',
            'Futures Fee ($)': 'sum',
            'Total Vol ($)': 'sum',
            'Total Fee ($)': 'sum',
            'Profit Fee ($)': 'sum',
            'Activate KOL': 'sum',
            'EFTTC': 'sum',
            'Bonus Consumption': 'sum',
            'Bonus Transfer Into': 'sum',
            'Futures PNL': 'sum'
        }).reset_index()
        
        # 按日期倒序排列（最新日期在上）
        daily_totals = daily_totals.sort_values('Date_dt', ascending=False).reset_index(drop=True)
        
        # 获取最新年月
        latest_year_month = daily_totals['YearMonth'].iloc[0]
        
        # 获取团队成员列表（从Dimension列中提取商务名称）
        dimensions = supervisor_data['Dimension'].unique()
        businesses = []
        for dim in dimensions:
            if ' - ' in dim:
                business_name = dim.split(' - ')[-1].strip()
                if business_name and business_name not in businesses:
                    businesses.append(business_name)
        business_list = ', '.join(businesses)
        
        # 准备列
        columns = [
            'Date', 'Reg', 'FTD', 'FTT', 'Deposit ($)', 'Withdraw ($)', 
            'Net Deposit ($)', 'DAU', 'Spot Vol ($)', 'Spot Fee ($)', 
            'Futures Vol ($)', 'Futures Fee ($)', 'Total Vol ($)', 'Total Fee ($)',
            'Profit Fee ($)', 'Activate KOL', 'EFTTC', 'Bonus Consumption', 
            'Bonus Transfer Into', 'Futures PNL'
        ]
        available_columns = [col for col in columns if col in daily_totals.columns]
        
        # 构建表格数据
        table_data = []
        month_groups = daily_totals.groupby('YearMonth', sort=False)
        
        # 为整个团队数据添加ISO周信息，用于处理跨月周
        full_team_data = daily_totals.copy()
        full_team_data['ISO_Year'] = full_team_data['Date_dt'].dt.isocalendar().year
        full_team_data['ISO_Week'] = full_team_data['Date_dt'].dt.isocalendar().week
        full_team_data['YearWeek'] = full_team_data['ISO_Year'].astype(str) + '-W' + full_team_data['ISO_Week'].astype(str).str.zfill(2)
        
        for year_month, month_data in month_groups:
            year = month_data['Year'].iloc[0]
            month = month_data['Month'].iloc[0]
            is_latest_month = (year_month == latest_year_month)
            is_complete = self.is_month_complete(month_data, year, month)
            
            if is_latest_month:
                # 最新月：显示每日数据
                # 为最新月数据添加周信息
                month_data_with_weeks = month_data.copy()
                month_data_with_weeks['ISO_Year'] = month_data_with_weeks['Date_dt'].dt.isocalendar().year
                month_data_with_weeks['ISO_Week'] = month_data_with_weeks['Date_dt'].dt.isocalendar().week
                month_data_with_weeks['YearWeek'] = month_data_with_weeks['ISO_Year'].astype(str) + '-W' + month_data_with_weeks['ISO_Week'].astype(str).str.zfill(2)
                
                # 显示每日数据并记录周信息
                week_groups = {}
                for _, row in month_data_with_weeks.iterrows():
                    formatted_row = []
                    for col in available_columns:
                        value = row[col]
                        if col == 'Date':
                            formatted_row.append(row['Date_dt'].strftime('%Y-%m-%d'))
                        else:
                            formatted_row.append(self.format_number(value))
                    table_data.append(formatted_row)
                    
                    # 记录每周的数据行索引
                    week_key = row['YearWeek']
                    if week_key not in week_groups:
                        week_groups[week_key] = []
                    week_groups[week_key].append(len(table_data) - 1)
                
                # 按周分组计算并添加周度统计
                for week_key, row_indices in week_groups.items():
                    # 获取该周的所有数据行（包括跨月的情况）
                    week_data = full_team_data[full_team_data['YearWeek'] == week_key]
                    
                    # 创建周度统计行：使用日期区间格式
                    start_date = week_data['Date_dt'].min()
                    end_date = week_data['Date_dt'].max()
                    week_total_label = f"{start_date.strftime('%m/%d')}~{end_date.strftime('%m/%d')}"
                    week_total_row = [week_total_label]
                    
                    for col in available_columns[1:]:
                        if col in ['DAU', 'Activate KOL']:
                            week_total_row.append(self.format_number(week_data[col].max()))
                        elif col == 'Reg':
                            week_total_row.append(self.format_number(week_data[col].sum()))
                        elif col == 'Onboard KOL':
                            week_total_row.append(self.format_number(week_data[col].sum()))
                        else:
                            week_total_row.append(self.format_number(week_data[col].sum()))
                    
                    table_data.append(week_total_row)
                
                # 最新月总和
                month_total_label = f"{year}/{month:02d}"
                month_total_row = [month_total_label]
                for col in available_columns[1:]:
                    if col in ['DAU', 'Activate KOL']:
                        month_total_row.append(self.format_number(month_data[col].max()))
                    elif col == 'Reg':
                        month_total_row.append(self.format_number(month_data[col].sum()))
                    elif col == 'Onboard KOL':
                        month_total_row.append(self.format_number(month_data[col].sum()))
                    else:
                        month_total_row.append(self.format_number(month_data[col].sum()))
                table_data.append(month_total_row)
                
            elif is_complete:
                # 历史完整月：只显示总和
                month_total_label = f"{year}/{month:02d}"
                month_total_row = [month_total_label]
                for col in available_columns[1:]:
                    if col in ['DAU', 'Activate KOL']:
                        month_total_row.append(self.format_number(month_data[col].max()))
                    elif col == 'Onboard KOL':
                        month_total_row.append(self.format_number(month_data[col].sum()))
                    else:
                        month_total_row.append(self.format_number(month_data[col].sum()))
                table_data.append(month_total_row)
        
        # 添加TOTAL行
        if len(daily_totals) > 0:
            total_row = ['TOTAL']
            for col in available_columns[1:]:
                if col in ['DAU', 'Activate KOL']:
                    total_row.append(self.format_number(daily_totals[col].max()))
                elif col == 'Onboard KOL':
                    total_row.append(self.format_number(daily_totals[col].sum()))
                else:
                    total_row.append(self.format_number(daily_totals[col].sum()))
            table_data.append(total_row)
        
        # 创建图表
        fig_height = max(len(table_data) * 0.4 + 3, 11)
        fig, ax = plt.subplots(figsize=(24, fig_height))
        ax.axis('tight')
        ax.axis('off')
        
        # 创建表格
        table = ax.table(
            cellText=table_data,
            colLabels=available_columns,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 0.92]
        )
        
        # 表格样式
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        
        # 表头
        for i in range(len(available_columns)):
            cell = table[(0, i)]
            cell.set_facecolor('#3d3d3d')
            cell.set_text_props(weight='bold', color='white', fontsize=9, ha='center')
            cell.set_height(0.08)
            cell.set_edgecolor('white')
            cell.set_linewidth(1.5)
        
        # 识别月总和行和周统计行
        month_summary_rows = []
        week_summary_rows = []
        for i, row_data in enumerate(table_data):
            row_label = str(row_data[0])
            if len(row_label) == 7 and '/' in row_label and row_label != 'TOTAL':
                month_summary_rows.append(i + 1)
            elif '~' in row_label:
                week_summary_rows.append(i + 1)
        
        # 设置行样式
        row_counter = 0
        for i in range(1, len(table_data) + 1):
            for j in range(len(available_columns)):
                cell = table[(i, j)]
                
                is_month_summary = i in month_summary_rows
                is_week_summary = i in week_summary_rows
                is_total = 'TOTAL' in str(table_data[i-1][0])
                
                if is_total:
                    # TOTAL行
                    cell.set_facecolor('#3d3d3d')
                    cell.set_text_props(weight='bold', color='white', fontsize=10, ha='center')
                    cell.set_height(0.07)
                    cell.set_edgecolor('white')
                    cell.set_linewidth(1.5)
                elif is_month_summary:
                    # 月总和行
                    cell.set_facecolor('#f9a825')
                    cell.set_text_props(weight='bold', color='white', fontsize=10, ha='center')
                    cell.set_height(0.07)
                    cell.set_edgecolor('white')
                    cell.set_linewidth(1.5)
                    row_counter = 0
                elif is_week_summary:
                    # 周统计行 - 浅蓝色背景
                    cell.set_facecolor('#b3e5fc')
                    cell.set_text_props(weight='bold', color='#0277bd', fontsize=10, ha='center')
                    cell.set_height(0.07)
                    cell.set_edgecolor('white')
                    cell.set_linewidth(1.5)
                    row_counter = 0
                else:
                    # 每日数据行
                    if row_counter % 2 == 0:
                        cell.set_facecolor('#f8f9fa')
                    else:
                        cell.set_facecolor('white')
                    cell.set_text_props(fontsize=9, ha='center')
                    cell.set_height(0.06)
                    cell.set_edgecolor('#e0e0e0')
                    cell.set_linewidth(0.5)
                    
                if not is_month_summary and not is_week_summary and not is_total:
                    if j == len(available_columns) - 1:
                        row_counter += 1
        
        # 添加标题
        title_y_position = 0.98
        fig.text(0.05, title_y_position, f"{supervisor_name} Team", 
                 fontsize=22, fontweight='bold', 
                 verticalalignment='top',
                 color='#2c3e50')
        
        # 副标题显示团队成员
        if business_list:
            fig.text(0.05, 0.95, f"Members: {business_list}", 
                     fontsize=10, style='italic',
                     verticalalignment='top',
                     color='#7f8c8d')
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.94, bottom=0.02)
        
        # 保存
        safe_name = supervisor_name.replace('/', '_').replace('\\', '_').replace(' ', '_')
        output_path = os.path.join(output_dir, f'{safe_name}_team_report.png')
        fig.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        
        return output_path
    
    def format_change_rate(self, current, previous):
        """计算并格式化变化率"""
        if pd.isna(previous) or previous == 0:
            if current > 0:
                return '+100%'
            else:
                return '0%'
        
        change_rate = ((current - previous) / abs(previous)) * 100
        
        if change_rate > 0:
            return f'+{change_rate:.1f}%'
        elif change_rate < 0:
            return f'{change_rate:.1f}%'
        else:
            return '0%'
    
    def create_supervisors_daily_report(self, data, output_path='supervisor_daily_comparison.png', days=1):
        """创建所有总监的每日数据对比报表（含日环比变化率）"""
        
        # 转换日期 - 使用正确的列名
        date_column = None
        for col in data.columns:
            if '日期' in col or 'date' in col.lower():
                date_column = col
                break
        
        if not date_column:
            print("⚠ 没有找到日期列")
            return None
            
        data['Date_dt'] = pd.to_datetime(data[date_column], errors='coerce')
        data = data[data['Date_dt'].notna()].copy()
        
        if len(data) == 0:
            print("⚠ 没有有效日期数据")
            return None
        
        # 按日期倒序排列，获取最近N天（用于计算变化率需要N+1天）
        data = data.sort_values('Date_dt', ascending=False).reset_index(drop=True)
        latest_date = data['Date_dt'].iloc[0]
        cutoff_date = latest_date - timedelta(days=days)  # 获取days+1天数据用于计算变化率
        recent_data = data[data['Date_dt'] >= cutoff_date].copy()
        
        # 获取所有总监 - 使用原始数据中的商务总监列
        supervisor_column = None
        for col in recent_data.columns:
            if '商务总监' in col or 'supervisor' in col.lower():
                supervisor_column = col
                break
        
        if not supervisor_column:
            print("⚠ 没有找到商务总监列")
            return None
            
        # 获取所有总监
        supervisors = recent_data[supervisor_column].unique()
        
        # 关键指标列
        key_metrics = [
            'Reg', 'FTD', 'FTT', 'Net Deposit ($)', 'DAU', 
            'Total Vol ($)', 'Total Fee ($)', 'Profit Fee ($)', 
            'Activate KOL', 'EFTTC', 'Futures PNL'
        ]
        
        # 获取所有总监并按最新一天的Total Vol降序排序
        supervisors_data = []
        for supervisor in supervisors:
            supervisor_data = recent_data[recent_data[supervisor_column] == supervisor].copy()
            supervisor_data = supervisor_data.sort_values('Date_dt', ascending=False).reset_index(drop=True)
            
            if len(supervisor_data) == 0:
                continue
            
            # 获取最新一天的Total Vol用于排序
            latest_total_vol = supervisor_data.iloc[0].get('Total Vol ($)', 0)
            supervisors_data.append({
                'supervisor': supervisor,
                'data': supervisor_data,
                'total_vol': latest_total_vol
            })
        
        # 按交易量降序排序
        supervisors_data.sort(key=lambda x: x['total_vol'], reverse=True)
        
        # 构建表格数据
        table_data = []
        
        for item in supervisors_data:
            supervisor = item['supervisor']
            supervisor_data = item['data']
            
            if len(supervisor_data) == 0:
                continue
            
            # 只取最新的一天数据，但需要前一天数据来计算变化率
            latest_row = supervisor_data.iloc[0]
            prev_row = supervisor_data.iloc[1] if len(supervisor_data) > 1 else None
            
            date_str = latest_row['Date_dt'].strftime('%Y-%m-%d')
            data_row = [supervisor]  # 第一列显示总监名称
            
            # 为每个指标添加数值和变化率（合并显示）
            for metric in key_metrics:
                # 安全获取当前值
                if metric in latest_row.index:
                    current_value = latest_row[metric]
                    if pd.isna(current_value):
                        current_value = 0
                else:
                    current_value = 0
                
                # 获取变化率
                if prev_row is not None:
                    # 安全获取前一天的值
                    if metric in prev_row.index:
                        prev_value = prev_row[metric]
                        if pd.isna(prev_value):
                            prev_value = 0
                    else:
                        prev_value = 0
                    
                    change_rate = self.format_change_rate(current_value, prev_value)
                else:
                    change_rate = '-'
                
                # 合并显示：数值 (变化率)
                combined_text = f"{self.format_number(current_value)} ({change_rate})"
                data_row.append(combined_text)
            
            table_data.append(data_row)
        
        # 创建列标题（不再需要单独的Δ%列）
        col_labels = ['Supervisor'] + key_metrics
        
        # 创建图表
        num_rows = len(table_data)
        num_cols = len(col_labels)
        
        fig_width = max(26, num_cols * 1.8)  # 增加列宽以容纳数值+变化率
        fig_height = max(num_rows * 0.5 + 3, 10)
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        ax.axis('tight')
        ax.axis('off')
        
        # 创建表格
        table = ax.table(
            cellText=table_data,
            colLabels=col_labels,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 0.95]
        )
        
        # 表格样式
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        
        # 表头样式
        for i in range(len(col_labels)):
            cell = table[(0, i)]
            if i == 0:
                cell.set_facecolor('#2c3e50')
            else:
                cell.set_facecolor('#34495e')
            cell.set_text_props(weight='bold', color='white', fontsize=8, ha='center')
            cell.set_height(0.05)
            cell.set_edgecolor('white')
            cell.set_linewidth(1)
        
        # 数据行样式
        row_counter = 0
        
        for i in range(1, num_rows + 1):
            for j in range(num_cols):
                cell = table[(i, j)]
                cell_text = str(table_data[i-1][j])
                
                if j == 0:  # 总监名称列
                    cell.set_facecolor('#1976d2')
                    cell.set_text_props(fontsize=9, ha='left', weight='bold', color='white')
                    cell.set_height(0.045)
                else:  # 数据列（包含数值和变化率）
                    # 根据变化率部分设置颜色
                    if '(+' in cell_text and '(+0%' not in cell_text and '(+0.0%' not in cell_text:
                        # 正增长 - 绿色
                        cell.set_facecolor('#c8e6c9')
                        cell.set_text_props(fontsize=8, ha='center', color='#2e7d32', weight='bold')
                    elif '(-' in cell_text and '(-)' not in cell_text and '(0%)' not in cell_text:
                        # 负增长 - 红色
                        cell.set_facecolor('#ffcdd2')
                        cell.set_text_props(fontsize=8, ha='center', color='#c62828', weight='bold')
                    else:
                        # 无变化或首日 - 灰色
                        if row_counter % 2 == 0:
                            cell.set_facecolor('#f8f9fa')
                        else:
                            cell.set_facecolor('white')
                        cell.set_text_props(fontsize=8, ha='center', color='#424242')
                    
                    cell.set_height(0.04)
                
                cell.set_edgecolor('#e0e0e0')
                cell.set_linewidth(0.5)
            
            row_counter += 1
        
        # 添加标题
        latest_date_str = latest_date.strftime('%Y-%m-%d')
        
        fig.text(0.5, 0.98, 'Supervisor Daily Performance Comparison', 
                 fontsize=20, fontweight='bold', 
                 ha='center', va='top',
                 color='#2c3e50')
        
        fig.text(0.5, 0.96, f'Date: {latest_date_str} | Sorted by Total Vol (Desc) | Format: Value (Change%)', 
                 fontsize=11, style='italic',
                 ha='center', va='top',
                 color='#7f8c8d')
        
        # 添加图例
        legend_elements = [
            mpatches.Rectangle((0, 0), 1, 1, fc='#c8e6c9', edgecolor='none', label='Increase'),
            mpatches.Rectangle((0, 0), 1, 1, fc='#ffcdd2', edgecolor='none', label='Decrease'),
            mpatches.Rectangle((0, 0), 1, 1, fc='#f5f5f5', edgecolor='none', label='No Change/N/A')
        ]
        
        ax.legend(handles=legend_elements, 
                 loc='upper right', 
                 bbox_to_anchor=(0.98, 0.98),
                 frameon=True,
                 fontsize=9)
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.94, bottom=0.02)
        
        # 保存
        fig.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        
        return output_path
    
    def create_bd_report(self, agent_name, agent_data, output_dir='bd_reports', kol_name=None):
        """为单个代理创建报表图片
        
        Args:
            agent_name: 代理名称
            agent_data: 代理数据
            output_dir: 输出目录
            kol_name: 总代理名称（如果为总代理数据）
        """
        result = self.create_table_data(agent_data, kol_name)
        if result is None:
            return None
        
        table_data, available_columns, business_name, supervisor = result
        fig = self.create_visualization(table_data, available_columns, business_name, supervisor)
        
        # 如果是总代理报表，使用特殊的保存路径
        if kol_name:
            output_path = self.save_kol_report(fig, business_name, supervisor, agent_data['Dimension'].iloc[0].split(' - ')[-1], output_dir)
        else:
            output_path = self.save_report(fig, business_name, supervisor, output_dir)
        
        return output_path
    
    def group_by_supervisor(self, result_df):
        """按总监分组"""
        supervisor_groups = {}
        dimensions = result_df['Dimension'].unique()
        
        for dimension in dimensions:
            if ' - ' in dimension:
                supervisor = dimension.split(' - ')[0].strip()
            else:
                supervisor = 'Other'
            
            if supervisor not in supervisor_groups:
                supervisor_groups[supervisor] = []
            supervisor_groups[supervisor].append(dimension)
        
        return supervisor_groups
    
    def generate_reports(self, processed_df=None, csv_file='raw_data.csv', output_dir='bd_reports'):
        """生成所有商务BD的报表
        
        Args:
            processed_df: 已处理的数据DataFrame（可选）
            csv_file: CSV文件路径（当processed_df为None时使用）
            output_dir: 输出目录
        """
        print("=" * 80)
        print("开始读取和处理数据...")
        print("=" * 80)
        
        # 如果传入了处理过的数据，直接使用；否则读取CSV
        if processed_df is not None:
            result = self.aggregate_data(processed_df)
        else:
            # 读取和处理数据
            df = pd.read_csv(csv_file)
            df = self.process_raw_data(df)
            result = self.aggregate_data(df)
        
        # 按总监分组
        supervisor_groups = self.group_by_supervisor(result)
        
        print(f"开始生成 {len(result['Dimension'].unique())} 个商务BD的报表图片...")
        print("=" * 80)
        
        generated_files = []
        
        # 按总监分组生成报表
        for supervisor in sorted(supervisor_groups.keys()):
            print(f"\n📁 总监: {supervisor}")
            print("-" * 80)
            
            for dimension in supervisor_groups[supervisor]:
                agent_data = result[result['Dimension'] == dimension].copy()
                output_path = self.create_bd_report(dimension, agent_data, output_dir)
                if output_path:
                    generated_files.append(output_path)
                    print(f"  ✓ {dimension} -> {output_path}")
        
        print("=" * 80)
        print(f"报表生成完成！共生成 {len(generated_files)} 个文件")
        print("=" * 80)
        
        return generated_files
    
    def generate_kol_reports(self, processed_df=None, csv_file='raw_data.csv', output_dir='agent_reports'):
        """生成所有总代理的报表
        
        Args:
            processed_df: 已处理的数据DataFrame（可选）
            csv_file: CSV文件路径（当processed_df为None时使用）
            output_dir: 输出目录
        """
        print("=" * 80)
        print("开始读取和处理总代理数据...")
        print("=" * 80)
        
        # 如果传入了处理过的数据，直接使用；否则读取CSV
        if processed_df is not None:
            result = self.aggregate_data_by_kol(processed_df)
        else:
            # 读取和处理数据
            df = pd.read_csv(csv_file)
            df = self.process_raw_data(df)
            result = self.aggregate_data_by_kol(df)
        
        if len(result) == 0:
            print("没有找到总代理数据")
            return []
        
        # 按总监和BD分组
        kol_groups = {}
        for _, row in result.iterrows():
            kol_name = row['总代理']
            dimension = row['Dimension']
            
            if ' - ' in dimension:
                parts = dimension.split(' - ')
                supervisor = parts[0].strip()
                bd_name = parts[-1].strip()
            else:
                supervisor = 'Other'
                bd_name = dimension
            
            key = (supervisor, bd_name, kol_name)
            if key not in kol_groups:
                kol_groups[key] = []
            kol_groups[key].append(row)
        
        print(f"开始生成 {len(kol_groups)} 个总代理的报表图片...")
        print("=" * 80)
        
        generated_files = []
        
        # 按总监分组生成总代理报表
        current_supervisor = None
        current_bd = None
        
        for (supervisor, bd_name, kol_name), kol_data in sorted(kol_groups.items()):
            if supervisor != current_supervisor:
                print(f"\n📁 总监: {supervisor}")
                print("-" * 80)
                current_supervisor = supervisor
                current_bd = None
            
            if bd_name != current_bd:
                print(f"  📂 BD: {bd_name}")
                current_bd = bd_name
            
            # 转换数据为DataFrame
            kol_df = pd.DataFrame(kol_data)
            output_path = self.create_bd_report(kol_name, kol_df, output_dir, kol_name)
            if output_path:
                generated_files.append(output_path)
                print(f"    ✓ {kol_name} -> {output_path}")
        
        print("=" * 80)
        print(f"总代理报表生成完成！共生成 {len(generated_files)} 个文件")
        print("=" * 80)
        
        return generated_files


def main():
    """主函数：生成所有类型的报表"""
    
    print("🚀 开始生成所有报表...")
    
    # 创建报表生成器
    generator = DailyReportGenerator()
    
    # 读取数据
    print("📊 读取数据文件...")
    try:
        df = pd.read_csv('raw_data.csv')
        print(f"✅ 成功读取数据，共 {len(df)} 行")
    except FileNotFoundError:
        print("❌ 未找到 raw_data.csv 文件")
        return
    except Exception as e:
        print(f"❌ 读取数据时出错: {e}")
        return
    
    # 处理原始数据
    print("🔧 处理原始数据...")
    processed_df = generator.process_raw_data(df)
    print(f"✅ 数据处理完成")
    
    # 1. 生成商务BD报表（按总监→商务BD分组）
    print("\n📈 1. 生成商务BD报表...")
    bd_reports = generator.generate_reports(processed_df)
    print(f"✅ 商务BD报表生成完成，共 {len(bd_reports)} 个报表")
    
    # # 2. 生成总代理报表（按总监→商务BD→总代理分组）
    # print("\n📈 2. 生成总代理报表...")
    # kol_reports = generator.generate_kol_reports(processed_df)
    # print(f"✅ 总代理报表生成完成，共 {len(kol_reports)} 个报表")
    kol_reports = []  # 初始化空列表，避免后续报错
    
    # 3. 生成团队报表（按总监生成团队报表）
    print("\n📈 3. 生成团队报表...")
    
    # 首先聚合数据
    aggregated_df = generator.aggregate_data(processed_df)
    
    # 按总监分组数据
    supervisor_groups = generator.group_by_supervisor(aggregated_df)
    team_reports = []
    
    for supervisor_name, supervisor_data in supervisor_groups.items():
        print(f"📝 生成 {supervisor_name} 的团队报表...")
        try:
            # 获取该总监的所有数据
            supervisor_df = aggregated_df[aggregated_df['Dimension'].str.startswith(supervisor_name + ' - ')]
            report_path = generator.create_supervisor_report(supervisor_name, supervisor_df)
            if report_path:
                team_reports.append(report_path)
                print(f"✅ {supervisor_name} 团队报表已生成: {report_path}")
        except Exception as e:
            print(f"❌ 生成 {supervisor_name} 团队报表时出错: {e}")
    
    print(f"✅ 团队报表生成完成，共 {len(team_reports)} 个报表")
    
    # 4. 生成总监对比报表（所有总监每日数据对比，含日环比变化率）
    print("\n📈 4. 生成总监对比报表...")
    try:
        comparison_report = generator.create_supervisors_daily_report(processed_df, output_path='supervisor_daily_comparison.png', days=1)
        if comparison_report:
            print(f"✅ 总监对比报表已生成: {comparison_report}")
    except Exception as e:
        print(f"❌ 生成总监对比报表时出错: {e}")
    
    # 总结
    print("\n" + "="*50)
    print("📊 报表生成完成！")
    print(f"商务BD报表: {len(bd_reports)} 个")
    print(f"总代理报表: {len(kol_reports)} 个") 
    print(f"团队报表: {len(team_reports)} 个")
    print(f"总监对比报表: 1 个")
    print("="*50)
    
    # 显示生成的文件结构
    print("\n📁 生成的文件结构:")
    
    if os.path.exists('bd_reports'):
        bd_dirs = [d for d in os.listdir('bd_reports') if os.path.isdir(os.path.join('bd_reports', d))]
        print(f"bd_reports/ - {len(bd_dirs)} 个总监文件夹")
    
    if os.path.exists('agent_reports'):
        agent_dirs = [d for d in os.listdir('agent_reports') if os.path.isdir(os.path.join('agent_reports', d))]
        print(f"agent_reports/ - {len(agent_dirs)} 个总监文件夹")
    
    if os.path.exists('supervisor_reports'):
        team_files = [f for f in os.listdir('supervisor_reports') if f.endswith('.png')]
        print(f"supervisor_reports/ - {len(team_files)} 个团队报表")
    
    if os.path.exists('supervisor_daily_comparison.png'):
        print("supervisor_daily_comparison.png - 总监对比报表")


if __name__ == "__main__":
    main()