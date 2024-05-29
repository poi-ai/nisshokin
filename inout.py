import csv
import logging
import inspect
import os
import sys
import re
import requests
from datetime import datetime, timedelta

class Log():
    '''
    loggerの設定を簡略化
        ログファイル名は呼び出し元のファイル名
        出力はINFO以上のメッセージのみ

    Args:
        output(int):出力タイプを指定
                    0:ログのみ出力、1:コンソールのみ出力、空:両方出力

    '''
    def __init__(self, filename = '', output = None):
        self.logger = logging.getLogger()
        self.output = output
        self.filename = filename
        self.today = self.now().strftime("%Y%m")
        self.set()

    def set(self):
        # 重複出力防止処理 / より深いファイルをログファイル名にする
        for h in self.logger.handlers[:]:
            # 起動中ログファイル名を取得
            log_path = re.search(r'<FileHandler (.+) \(INFO\)>', str(h))
            # 出力対象/占有ロックから外す
            self.logger.removeHandler(h)
            h.close()
            # ログファイルの中身が空なら削除
            if log_path != None:
                if os.stat(log_path.group(1)).st_size == 0:
                    os.remove(log_path.group(1))

        # フォーマットの設定
        formatter = logging.Formatter(f'%(asctime)s {self.filename.rjust(2, " ")} -  [%(levelname)s] %(message)s')

        # 出力レベルの設定
        self.logger.setLevel(logging.INFO)

        # ログ出力設定
        if self.output != 1:
            # リポジトリのルートフォルダを指定
            log_folder = os.path.join(os.path.dirname(__file__), 'log')
            # ログフォルダチェック。無ければ作成
            if not os.path.exists(log_folder):
                os.makedirs(log_folder)
            # 出力先を設定
            handler = logging.FileHandler(filename = os.path.join(log_folder, f'{self.now().strftime("%Y%m")}.log'), encoding = 'utf-8')
            # 出力レベルを設定
            handler.setLevel(logging.INFO)
            # フォーマットの設定
            handler.setFormatter(formatter)
            # ハンドラの適用
            self.logger.addHandler(handler)

        # コンソール出力設定
        if self.output != 0:
            # ハンドラの設定
            handler = logging.StreamHandler(sys.stdout)
            # 出力レベルを設定
            handler.setLevel(logging.INFO)
            # フォーマットの設定
            handler.setFormatter(formatter)
            # ハンドラの適用
            self.logger.addHandler(handler)

    def now(self):
        '''現在のJSTを取得'''
        return datetime.utcnow() + timedelta(hours = 9)

    def debug(self, message):
        file_name, line = self.call_info(inspect.stack())
        self.logger.debug(f'{message} [{file_name} in {line}]')

    def info(self, message):
        file_name, line = self.call_info(inspect.stack())
        self.logger.info(f'{message} [{file_name} in {line}]')

    def warning(self, message):
        file_name, line = self.call_info(inspect.stack())
        self.logger.warning(f'{message} [{file_name} in {line}]')

    def error(self, message):
        file_name, line = self.call_info(inspect.stack())
        self.logger.error(f'{message} [{file_name} in {line}]')

    def critical(self, message):
        file_name, line = self.call_info(inspect.stack())
        self.logger.critical(f'{message} [{file_name} in {line}]')

    def call_info(self, stack):
        '''
        ログ呼び出し元のファイル名と行番号を取得する

        Args:
            stack(list): 呼び出し元のスタック

        Returns:
            os.path.basename(stack[1].filename)(str): 呼び出し元ファイル名
            stack[1].lineno(int): 呼び出し元行番号

        '''
        return os.path.basename(stack[1].filename), stack[1].lineno

class Line():
    def __init__(self):
        self.TOKEN = self.get_token()

    def get_token(self):
        '''line_token.txtからトークンを取得する'''
        try:
            with open('line_token.txt', 'r') as file:
                token = file.read().strip()
                return token if token else ''
        except Exception: # ファイルが存在しない場合とか
            return ''

    def send(self, message):
        '''
        LINE Notifyを用いてメッセージを送信する

        Args:
            message(str) : LINE送信するメッセージ内容
        '''
        TOKEN = ''

        # LINEトークンを取得
        with open('line_token.txt', 'r') as file:
            TOKEN = file.read().strip()

        if TOKEN == '': return

        # リクエスト内容を設定
        headers = {'Authorization': f'Bearer {TOKEN}'}
        data = {'message': f'{message}'}

        # メッセージ送信
        requests.post('https://notify-api.line.me/api/notify', headers = headers, data = data)


class Csv():
    def get(self, file_name):
        '''
        CSVファイルからデータを取得する

        Args:
            file_name(str): ファイル名(拡張子なし)

        Return:
            rows(list[list[]]): CSVのデータ
        '''
        with open(f'{file_name}.csv', 'r', encoding = 'utf-8') as f:
            rows = list(csv.reader(f))
        return rows

    def add(self, file_name, data, single = True):
        '''
        CSVファイルへデータを追記する

        Args:
            file_name(str): 書き込み先のCSVファイル名(拡張子なし)
            data(str): 書き込むデータ
            single(bool): 書き込む行は一行か複数行か
        '''
        with open(f'{file_name}.csv', 'a', encoding = 'utf-8', newline = '') as f:
            writer = csv.writer(f, lineterminator = '\n')
            if single:
                writer.writerow(data)
            else:
                writer.writerows(data)

    def move(self, year):
        '''一時ファイルに保存したデータを移動させる'''

        # 一時ファイルからデータ読み込み
        data = self.csv.get(f'tmp_nisshokin_data_{year}')

        # 記録用のCSVにデータ書き込み
        self.csv.add(f'nisshokin_data_{year}', data, single = False)

        # 一時ファイル削除
        os.remove(f'tmp_nisshokin_data_{year}.csv')