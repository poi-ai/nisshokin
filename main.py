import csv
import itertools
import inout
import time
import traceback
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

class Main():
    def __init__(self):
        self.log = inout.Log()
        self.line = inout.Line()
        self.csv = inout.Csv()
        self.now = datetime.utcnow() + timedelta(hours = 9)

    def main(self):
        '''主処理'''

        # 現在の日付に応じて処理を変えるためのフラグ
        date_type = self.date_check()
       
        month_first_business_day = self.now.date().day == 1 or (self.now.date().day <= 3 and self.now.date().weekday() == 0)
        # 月曜日
       

        # 営業日でない場合は残高が更新されないので取得処理を行わない
        if self.now.weekday() >= 5:
            exit()

        # 取得対象でない銘柄の証券コードリストと銘柄の最新取得日をCSVから取得
        self.log.info('銘柄情報CSV読み込み開始')
        try:
            na_stock_code_list, recorded_date_dict = self.extruct_stock_code()
        except Exception as e:
            self.error_output('銘柄情報CSV読み込み処理でエラー', e, traceback.format_exc())
            exit()
        self.log.info('銘柄情報CSV読み込み終了')

        # 証券コード1000 ~ 9999
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

            # 最新データが30日以上前の場合は月初にしかチェックしない
            if not month_first_business_day:
                if recorded_date != '0001/01/01' and datetime.strptime(recorded_date, '%Y/%m/%d').date() <= now.date() - timedelta(days = 30):
                    continue

            # IR BANKから日証金情報を取得
            self.log.info(f'銘柄コード: {stock_code}の日証金情報取得処理開始')
            url = f'https://irbank.net/{stock_code}/nisshokin'
            try:
                self.get_data(str(stock_code), url, recorded_date, True)
            except Exception as e:
                self.error_output('日証金情報取得処理でエラー', e, traceback.format_exc())
            self.log.info(f'銘柄コード: {stock_code}の日証金情報取得処理終了')

        # 貸株が異常増減したデータのレポートを作成し、LINEで送信する
        try:
            # レポートを作成する
            self.log.info(f'レポート作成処理開始')
            report = self.create_report()
            self.log.info(f'レポート作成処理終了')

            # レポートをLINEで送信する
            self.log.info(f'レポート送信処理開始')
            self.line.send(report)
            self.log.info(f'レポート送信処理終了')
        except Exception as e:
            self.error_output('レポート作成・送信処理でエラー', e, traceback.format_exc())

        # 一時ファイルの情報を写し、一時ファイルを削除する
        try:
            self.log.info(f'一時ファイル転記処理開始')
            self.csv.move(now.strftime('%y'))
            self.log.info(f'一時ファイル転記処理終了')
        except Exception as e:
            self.error_output('一時ファイル転記処理でエラー',e, traceback.format_exc())

    def date_check(self):
        '''
        現在の日付の種別を判定する

        Returns:
            date_type(int): 日付のタイプ
                0: 非営業日、1: 月初めの営業日、2: 週初めの営業日


        '''
        # 土日判定
        if self.now.weekday() >= 5:
            return 0

        # APIから祝日を取得
        holidays = self.get_holidays()
        if holidays == False:
            return False

        # 祝日判定
        if self.now.strftime('%Y-%m-%d') in holidays:
            return 0

        # 年末年始判定
        # result = self.check_new_year_holidays()

        # 週初め判定
        if self.now.weekday() == 0:
            return 1
        
        

    def get_holidays(self):
        '''
        Holidays JP APIから祝日情報を取得する

        Returns:
            holidays(dict): 実行日の昨年～来年までの祝日一覧

        '''
        try:
            r = requests.get('https://holidays-jp.github.io/api/v1/date.json')
        except Exception as e:
            self.log.error(f'祝日情報取得APIエラー\n{e}')
            return False

        if r.status_code != 200:
            self.log.error(f'祝日情報取得APIエラー ステータスコード: {r.status_code}')
            return False

        holidays = r.json()

        if len(holidays) == 0:
            self.log.error(f'祝日情報取得APIエラー レスポンス情報が空')
            return False

        return holidays

    def check_new_year_holidays(self):
        '''
        年末年始の休場期間か判定する

        '''
        #TODO
        pass

    def extruct_stock_code(self):
        '''取得対象でない銘柄の証券コードリストと銘柄の最新取得日をCSVから取得'''

        # 対象外の証券コードをCSVから取得
        na_stock_code_list = [code_list[1] for code_list in self.csv.get('na_stock_code')]

        # 各銘柄の最新取得日をCSVから取得
        recorded_date_dict = dict((row[0], row[1]) for row in self.csv.get('recorded_date'))

        return na_stock_code_list, recorded_date_dict

    def get_data(self, stock_code, url, recorded_date, latest_flag):
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
            self.csv.add('na_stock_code', [stock_code, time.strftime('%Y/%m/%d'), 'not exist'])
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
                self.get_data(stock_code, add_data_url, recorded_date, False)
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
            kashikabu_type = self.mold_text(td_info[2]).split(',')
            # 融資残/増減
            yushi_zan = td_info[3].text.replace(',', '').replace('-', '+-').split('+')
            if len(yushi_zan) == 1: yushi_zan.append('0')
            # 融資内訳(新規/返済)
            yushi_type = self.mold_text(td_info[4]).split(',')

            # データをCSVに一時ファイルのCSVに書き込む
            row = [stock_code, date, kashikabu_zan[0], kashikabu_zan[1], kashikabu_type[0], kashikabu_type[1],
                    yushi_zan[0], yushi_zan[1], yushi_type[0], yushi_type[1]]
            self.csv.add(f'tmp_nisshokin_data_{year}', row)

            # 記録済み日付管理CSVの日付より最新の日付データを取得した場合はCSVを更新する
            if latest_flag:
                # CSVから同じコードの行があるかチェック
                rows = self.csv.get('recorded_date')

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
                with open('recorded_date.csv', 'w', newline = '') as file:
                    writer = csv.writer(file)
                    writer.writerows(rows)

                latest_flag = False

        return True

    def mold_text(self, content):
        '''bs4.element.Tag型のデータから改行をカンマに変え他のHTMLタグは取り除く'''
        text = ''
        for content in content.contents:
            if isinstance(content, str):
                text += content
            elif content.name == 'br':
                text += ','
        return text

    def get_price(self, stock_code):
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
            self.csv.add('failed_stock_code', [stock_code, time.strftime('%Y/%m/%d'), 'not get price'])
            return False
        else:
            # 取れたら削除
            rows = self.csv.get('failed_stock_code')
            data = [row for row in rows if str(row[0]) != str(stock_code)]

            with open('failed_stock_code.csv', 'w', encoding = 'utf-8', newline = '') as file:
                writer = csv.writer(file)
                writer.writerows(data)

        # 300億以上は対象外
        if int(price) >= 30000:
            self.csv.add('na_stock_code', [stock_code, time.strftime('%Y/%m/%d'), 'too big'])
            return False

        return True

    def create_report(self):
        '''貸株に異常な増減のあった銘柄を抽出してレポートを作成する'''
        global now

        report = f'【{now.strftime("%m/%d")}の日証金増減レポート】\n'
        target_flag = False

        # 今回のプロセスで取得したデータを取得
        rows = self.csv.get(f'tmp_nisshokin_data_{now.strftime("%y")}')

        for row in rows:
            # 貸株が5000株以上増かつ前日比80%以上増 TODO 0除算チェック
            if (row[3] >= 5000) and (row[3] / row[2] >= 0.8):
                report += f'[{row[0]}] {row[1]} 残: {row[2]} / 増減: {row[3]}\n'
                target_flag = True

            # 貸株が5000株以上減かつ前日比80%以上減
            if (row[3] <= -5000) and (row[3] / row[2] <= -0.8):
                report += f'[{row[0]}] {row[1]} 残: {row[2]} / 増減: {row[3]}\n'
                target_flag = True

        if not target_flag: report += '異常増減した銘柄はありませんでした'

        return report

    def error_output(self, message, e = None, stacktrace = None):
            '''
            エラー時のログ出力/LINE通知を行う
            Args:
                message(str) : エラーメッセージ
                e(str) : エラー名
                stacktrace(str) : スタックトレース(traceback.format_exc())
            '''
            line_message = message
            self.log.error(message)

            if e != None:
                self.log.error(e)
                line_message += f'\n{e}'

            if stacktrace != None:
                self.log.error(stacktrace)
                line_message += f'\n{stacktrace}'

            self.line.send(line_message)

if __name__ == '__main__':
    m = Main()
    m.date_check()
    #m.main()