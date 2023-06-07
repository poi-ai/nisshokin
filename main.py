import csv
import datetime
import itertools
import pytz
import time
import re
import requests
from bs4 import BeautifulSoup

def main():
    '''主処理'''
    # 曜日チェック
    jst = pytz.timezone('Asia/Tokyo')
    weekday = datetime.datetime.now(jst).weekday()

    # 前日が営業日でない場合は取得しない
    if weekday == 5 or weekday == 6:
        exit()

    # 対象外の証券コードをCSVから取得
    na_stock_code_list = []
    with open('na_stock_code.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            na_stock_code_list.append(row[0])

    # 各銘柄の最新取得日をCSVから取得
    recorded_date_dict = {}
    with open('recorded_date.csv', 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            recorded_date_dict[row[0]] = row[1]

    # 証券コード1000~9999
    for stock_code in range(1000, 10000):
        # 対象外の証券コードの場合はスキップ
        if str(stock_code) in na_stock_code_list:
            continue

        '''
        一度全銘柄でチェックを入れたので当分はチェックを入れない
        処理最適化後に入れる
        ただ毎日入れるのは時間がかかりすぎるので、月1とか?

        # みんかぶから上場廃止/時価総額チェック
        result = get_price(stock_code)
        # 上場廃止or時価総額500億以上ならパス
        if not result:
            continue
        '''

        # 指定した証券コードの最新データ日(≠最新取得日)を取得
        if str(stock_code) in recorded_date_dict:
            recorded_date = recorded_date_dict[str(stock_code)]
        else:
            # CSVにデータがない(=記録したことがない)銘柄は最新取得日を1年にする
            recorded_date = '0001/01/01'

        # IR BANKから日証金情報を取得
        url = f'https://irbank.net/{stock_code}/nisshokin'
        result = get_data(str(stock_code), url, recorded_date, True)

        # 処理に失敗した場合
        if not result:
            raise


def get_data(stock_code, url, recorded_date, latest_flag):
    '''指定したURLに記載されている日証金情報を取得

    Args:
        stock_code(str): 取得対象の証券コード
        url(str): 取得対象ページのURL
        recorded_date(str,yyyy/mm/dd): 記録済みデータの中で最新の日付
        ※これ以前の日付のデータは取得しない
        latest_flag(bool): 取得対象が最新の日付を含むか

    Return:
        result(bool): 処理が正常に完了したか(取得対象が1件以上存在したか。ではない)
    '''
    # HTML取得
    time.sleep(2)
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'lxml')

    # 日証金テーブルの切り出し
    table = soup.find('table', class_ = 'bar')

    # テーブルがない(=日証金情報がない)場合は取得対象外の証券コードとしてCSVに書き込み
    if table is None:
        with open('na_stock_code.csv', 'a', encoding = 'utf-8', newline = '') as f:
            writer = csv.writer(f, lineterminator = '\n')
            writer.writerow([stock_code, time.strftime('%Y/%m/%d'), 'not exist'])
        return True

    tbody = table.find('tbody')
    tr_list = tbody.find_all('tr')

    year = -1

    for tr in tr_list:
        # 年度記載列の場合年度を更新
        td_year = tr.find('td', class_ = 'ct')
        if not td_year is None:
            year = int(td_year.text)
            # 2019年以前のデータは取らない
            if year <= 2019:
                return True
            continue

        # 年度記載以外の場合
        td_info = tr.find_all('td')

        # 追加読み込みボタン列か日証金情報が載っている列か判定
        if len(td_info) == 1:
            a_tag = td_info[0].find('a')
            # 追加読込先のURL取得
            link = str(a_tag.get('href'))
            add_data_url = f'https://irbank.net/{link}'

            # 再帰で追加読み込みされたデータを再帰で読み込み
            get_data(stock_code, add_data_url, recorded_date, False)
            continue

        # 各データ切り出し
        # 日付
        date = f'{year}/{td_info[0].text}'

        # 既に記録済みの最新日より古い日付のデータは記録しない
        if date <= recorded_date:
            return True

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

        # 記録済み日付管理CSVの日付より最新の日付データを取得した場合はCSVを更新する
        if latest_flag:
            # CSVから同じコードの行があるかチェック
            with open('recorded_date.csv', 'r', newline='') as file:
                reader = csv.reader(file)
                rows = list(reader)

                found_flag = False
                for row in rows:
                    if row[0] == stock_code:
                        row[1] = date
                        found_flag = True
                        break

                # 無ければ末尾に追記
                if not found_flag:
                    rows.append([str(stock_code), date])  # 新しい行を末尾に追加

            # 更新したデータを上書き
            with open('recorded_date.csv', 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(rows)

            latest_flag = False

    return True

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
    time.sleep(2)
    r = requests.get(f'https://minkabu.jp/stock/{stock_code}')
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
        price_match = re.search('時価総額([0-9,]+)百万円', tr.text.replace('\n', ''))
        if price_match != None:
            price = price_match.groups()[0].replace(',', '')

    # 取れなかったらエラーとしてファイルに書き込む、取れたら削除
    if int(price) == -1:
        with open('failed_stock_code.csv', 'a', encoding = 'utf-8', newline = '') as f:
            writer = csv.writer(f, lineterminator = '\n')
            writer.writerow([stock_code, time.strftime('%Y/%m/%d'), 'not get price'])
        return False
    else:
        # 取れたら削除
        with open('failed_stock_code.csv', "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            rows = [row for row in reader if str(row[0]) != str(stock_code)]

        with open('failed_stock_code.csv', "w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(rows)

    # 300億以上は対象外
    if int(price) >= 30000:
        with open('na_stock_code.csv', 'a', encoding = 'utf-8', newline = '') as f:
            writer = csv.writer(f, lineterminator = '\n')
            writer.writerow([stock_code, time.strftime('%Y/%m/%d'), 'too big'])
        return False

    return True

def create_report():
    '''貸株に異常な増減のあった銘柄を抽出'''
    report = ''

    return report

def line_send(message):
    ''' LINE Notify経由でメッセージを送信する

    Args:
        message(str) : LINE送信するメッセージ内容

    '''
    TOKEN = ''

    # リクエスト内容を設定
    headers = {'Authorization': f'Bearer {TOKEN}'}
    data = {'message': f'{message}'}

    # メッセージ送信
    requests.post('https://notify-api.line.me/api/notify', headers = headers, data = data)

if __name__ == '__main__':
    main()
    #get_price(1305)
    #get_price(7203) # ファストリ
    #get_price(2172) # インサイト


# TODO エラーが出たときのリカバリ処理(try-except)
## TODO 特に一部データ取得成功で一部失敗とかいう場合