import pandas as pd

# CSVファイルを読み込む
df = pd.read_csv('nisshokin_data_2023.csv')

# 条件1: 貸株(増減)が-5000以下かつ貸株(増減)/貸株残が-0.8以下の行
condition1 = (df['貸株(増減)'] <= -5000) & (df['貸株(増減)'] / df['貸株残'] <= -0.8)

# 条件2: 貸株(増減)が5000以上かつ貸株(増減)/貸株残が0.8以上の行
condition2 = (df['貸株(増減)'] >= 5000) & (df['貸株(増減)'] / df['貸株残'] >= 0.8)

# 条件を満たす行のみ抽出
filtered_df = df[condition1 | condition2]

# 証券コードごとの行数を計算してソートして表示
code_counts = filtered_df['証券コード'].value_counts().sort_values()
for code, count in code_counts.items():
    print(f"{code}: {count}")

# 抽出結果を新しいCSVファイルに保存する（文字コード: UTF-8）
filtered_df.to_csv('filtered_nisshokin_data.csv', index=False, encoding='utf-8')
