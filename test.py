import csv
import requests
from bs4 import BeautifulSoup

delete_target_code = []
updated_rows = []

# CSVファイルの読み込み
with open('failed_stock_code.csv', 'r', encoding = 'UTF-8') as f:
    reader = list(csv.reader(f))
    rows = list(reader)

    for row in rows:
        r = requests.get(f'https://minkabu.jp/stock/{row[0]}')
        soup = BeautifulSoup(r.text, 'lxml')
        if 'ページが見つかりませんでした' in soup:
            delete_target_code.append(row[0])
        exit()

# 削除対象でない列を取得
for row in rows:
    if row[0] not in delete_target_code:
        updated_rows.append(row)

# 更新された行をCSVファイルに書き込む 怖いんでいったん別ファイルに
with open('fixed_failed_stock_code.csv', 'w', encoding='UTF-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(updated_rows)
