import csv
import time
import requests
from bs4 import BeautifulSoup

# 対象外の証券コードをCSVから取得
na_stock_code_list = []
with open('na_stock_code.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        na_stock_code_list.append(row[0])

# 証券コード1000~9999
for stock_code in range(1000, 100000):
    # 対象外の証券コードの場合はスキップ
    if str(stock_code) in na_stock_code_list:
        continue

    # IR BANKから日証金情報を取得
    url = f'https://irbank.net/{stock_code}/nisshokin'
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')

    # 日証金テーブルの取得
    time.sleep(5)
    table = soup.find('table', class_='bar')

    # テーブルがない(=日証金情報がない)場合は対象外の証券コードとしてCSVに書き込み
    if table is None:
        with open('na_stock_code.csv', 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow([stock_code, time.strftime('%Y/%m/%d')])
        continue

    tbody = table.find('tbody')
    trs = tbody.find_all('tr')

    years = -1

    for index, tr in enumerate(trs):
        pass