import logging
import os
import sys
from datetime import datetime

class NisshokinLog():
    '''
    logの設定・出力を行う

    Args:
        stdout(bool): 標準出力も併せて行うか
    '''
    def __init__(self, stdout = True):
        self.logger = logging.getLogger()
        self.stdout = stdout
        self.date = datetime.now().strftime("%Y%m%d")
        self.set()

    def set(self):
        '''初期設定'''
        # 出力フォーマット設定
        formatter = logging.Formatter(f'%(asctime)s - [%(levelname)s] %(message)s')

        # 出力レベル設定
        self.logger.setLevel(logging.INFO)

        # ログフォルダチェック。無ければ作成
        log_folder = os.path.join(os.path.dirname(__file__), '..', 'log')
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        # ログ出力のハンドラ設定
        handler = logging.FileHandler(filename = os.path.join(log_folder, f'{self.date()}.log'), encoding = 'utf-8')
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # コンソール出力のハンドラ設定
        if self.stdOut:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def date_check(self):
        '''日付変更チェック'''
        if self.date != datetime.now().strftime("%Y%m%d"):
            self.date = datetime.now().strftime("%Y%m%d")
            # PG起動中に日付を超えた場合はログ名を設定しなおす
            self.set()

    def debug(self, message):
        self.date_check()
        self.logger.debug(message)

    def info(self, message):
        self.date_check()
        self.logger.info(message)

    def warning(self, message):
        self.date_check()
        self.logger.warning(message)

    def error(self, message):
        self.date_check()
        self.logger.error(message)

    def critical(self, message):
        self.date_check()
        self.logger.critical(message)