import csv
import os
import time
import requests
from bs4 import BeautifulSoup

file_created = False

def main():
    '''主処理'''
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
        # 取得関数呼び出し
        get_data(str(stock_code), url)


def get_data(stock_code, url):
    '''指定したURLに記載されている日証金情報を取得'''
    global file_created
    time.sleep(1)

    # HTML取得
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')

    # 日証金テーブルの切り出し
    table = soup.find('table', class_ = 'bar')

    # テーブルがない(=日証金情報がない)場合は取得対象外の証券コードとしてCSVに書き込み
    if table is None:
        with open('na_stock_code.csv', 'a', encoding = 'utf-8', newline = '') as f:
            writer = csv.writer(f, lineterminator = '\n')
            writer.writerow([stock_code, time.strftime('%Y/%m/%d')])
        return

    tbody = table.find('tbody')
    tr_list = tbody.find_all('tr')

    years = -1

    for tr in tr_list:
        # 年度記載列の場合年度を更新
        td_year = tr.find('td', class_ = 'ct')
        if not td_year is None:
            years = int(td_year.text)
            continue

        # 年度記載以外の場合
        td_info = tr.find_all('td')

        # 追加読み込みボタン列か日証金情報が載っている列か判定
        if len(td_info) == 1:
            a = td_info[0].find('a')
            # 追加読込先のURL取得
            link = str(a.get('href'))
            add_data_url = f'https://irbank.net/{link}'

            # 再帰で追加読み込みされたデータを再帰で読み込み
            get_data(stock_code, add_data_url)
            continue

        # 各データ切り出し
        # 日付
        date = f'{years}/{td_info[0].text}'
        # 貸株残/増減
        kashikabu_zan = td_info[1].text.replace(',', '').replace('-', '+-').split('+')
        if len(kashikabu_zan) == 1: kashikabu_zan.append('0')
        # 貸株内訳(新規/返済)
        kashikabu_type = br_to_comma(td_info[2]).split(',')
        # 融資残/増減
        yushi_zan = td_info[3].text.replace(',', '').replace('-', '+-').split('+')
        if len(yushi_zan) == 1: yushi_zan.append('0')
        # 融資内訳(新規/返済)
        yushi_type = br_to_comma(td_info[4]).split(',')

        # CSVファイルのパスとカラム名
        csv_file = 'nisshokin_data.csv'

        if file_created == False:
            columns = ['stock_code', 'date', 'kashikabu', 'kashikabu_change', 'kashikabu_new', 'kashikabu_repay',
                        'yushi', 'yushi_change', 'yushi_new', 'yushi_repay']

            # CSVファイルが存在しない場合は新規作成し、カラム名を書き込む
            if not os.path.exists(csv_file):
                with open(csv_file, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(columns)
            file_created = True

        # データをCSVに追記する
        with open(csv_file, 'a', newline='') as file:
            writer = csv.writer(file)

            row = [stock_code, date, kashikabu_zan[0], kashikabu_zan[1], kashikabu_type[0], kashikabu_type[1],
                   yushi_zan[0], yushi_zan[1], yushi_type[0], yushi_type[1]]
            writer.writerow(row)


def br_to_comma(content):
    '''bs4.element.Tag型のデータから改行をカンマに変え他のHTMLタグは取り除く'''
    text = ''
    for content in content.contents:
        if isinstance(content, str):
            text += content
        elif content.name == 'br':
            text += ','
    return text

if __name__ == '__main__':
    main()


# TODO 容量削減のために2020年くらいまででリミッターかけとく？
# memo L57 >= 2019でcontinue
# TODO 二度走らせた時に同じデータを書き込まないように
# memo 証券コード, 日付でユニーク
### TODO 毎度でかいcsvを読み込ませたくはない
### 年ごとにわけるか、重複防止用のユニークだけ記載したファイルを別途作るか
### TODO 一回でもユニークチェックに引っかかったらそれ以前の日付はすでに取得済みとみなしてcontinue
# TODO 時価総額1000億以上の企業は除外リストに追加しておく(仕手は1000億には仕掛けないでしょ。。。500億でもいい気はするけど)
# どっから取るかは要検討