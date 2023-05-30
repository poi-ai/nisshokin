import csv
import itertools
import time
import re
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

        # みんかぶから上場廃止/時価総額チェック
        result = get_price(stock_code)
        if not result:
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
            writer.writerow([stock_code, time.strftime('%Y/%m/%d'), 'not exist'])
        return

    tbody = table.find('tbody')
    tr_list = tbody.find_all('tr')

    year = -1

    for tr in tr_list:
        # 年度記載列の場合年度を更新
        td_year = tr.find('td', class_ = 'ct')
        if not td_year is None:
            year = int(td_year.text)
            # 2019年以前のデータは取らない
            if year == 2019:
                return
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
        date = f'{year}/{td_info[0].text}'
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

        # データをCSVに追記する
        with open(f'nisshokin_data_{year}.csv', 'a', newline='') as file:
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

def get_price(stock_code):
    '''みんかぶから上場廃止と時価総額を取ってくる'''
    #time.sleep(2)
    URL = f'https://minkabu.jp/stock/{stock_code}'
    r = requests.get(URL)
    soup = BeautifulSoup(r.content, 'lxml')

    # 上場廃止チェック
    if '上場廃止</em>になりました' in str(soup):
        with open('na_stock_code.csv', 'a', encoding = 'utf-8', newline = '') as f:
            writer = csv.writer(f, lineterminator = '\n')
            writer.writerow([stock_code, time.strftime('%Y/%m/%d'), 'delisting'])
        return False

    # 時価総額チェック
    price = -1
    tables = soup.find_all('table', class_ = 'md_table theme_light')
    trs = list(itertools.chain.from_iterable([table.find_all('tr') for table in tables]))

    for tr in trs:
        price_match = re.search('時価総額(.+)百万円', tr.text)
        if price_match != None:
            price = price_match.groups()[0].replace(',', '')

    # 取れなかったらエラー
    if int(price) == -1:
        pass # TODO エラー処理

    # 500億以上は対象外
    if int(price) >= 50000:
        with open('na_stock_code.csv', 'a', encoding = 'utf-8', newline = '') as f:
            writer = csv.writer(f, lineterminator = '\n')
            writer.writerow([stock_code, time.strftime('%Y/%m/%d'), 'too big'])
        return False

    return True


if __name__ == '__main__':
    main()
    #get_price(7203) # ファストリ
    #get_price(2172) # インサイト


# TODO 二度走らせた時に同じデータを書き込まないように
# memo 証券コード, 日付でユニーク
### TODO 毎度でかいcsvを読み込ませたくはない
### 年ごとにわけるか、重複防止用のユニークだけ記載したファイルを別途作るか
### TODO 一回でもユニークチェックに引っかかったらそれ以前の日付はすでに取得済みとみなしてcontinue
# TODO エラーが出たときのリカバリ処理(try-except)