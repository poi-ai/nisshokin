import pandas as pd

# CSVファイルを読み込む
df = pd.read_csv('nisshokin_data_2023.csv')

# 貸株が5000株以上減かつ前日比80%以上減
condition1 = (df['貸株(増減)'] <= -5000) & (df['貸株(増減)'] / df['貸株残'] <= -0.8)

# 貸株が5000株以上増かつ前日比80%以上増
condition2 = (df['貸株(増減)'] >= 5000) & (df['貸株(増減)'] / df['貸株残'] >= 0.8)

# 条件を満たす行のみ抽出
filtered_df = df[condition1 | condition2]

# 証券コードごとの行数を計算してソートして表示
code_counts = filtered_df['証券コード'].value_counts().sort_values()
for code, count in code_counts.items():
    print(f"{code}: {count}")

# 抽出結果を新しいCSVファイルに保存する（文字コード: UTF-8）
filtered_df.to_csv('filtered_nisshokin_data.csv', index=False, encoding='utf-8')
