from Information import Information
import time
import pandas as pd
from datetime import datetime as dt


class Recorder(Information):

    def __init__(self):
        super().__init__()

    def market_recorder(self, product, path):

        ticker = self.api.ticker(product_code=product)
        board = self.api.board(product_code=product)

        time = ticker['timestamp']
        last_price = ticker['ltp']  # 最終取引値 -> 値動きの判断に利用する
        mid_price = board['mid_price']

        time = time.replace("T", " ")

        if time.find(".") == - 1:
            tdatetime = dt.strptime(time, '%Y-%m-%d %H:%M:%S')
            tdatetime = tdatetime.timestamp()
        else:
            tdatetime = dt.strptime(time, '%Y-%m-%d %H:%M:%S.%f')
            tdatetime = tdatetime.timestamp()

        time = tdatetime

        print(time)

        w = pd.DataFrame([[time, last_price, mid_price]])  # 取得したティッカーをデータフレームに入れる

        w.to_csv(path, index=False, encoding="utf-8", mode='a', header=False)  # append to the CSV

    def balance_recorder(self, balance, order_price):

        time = self.api.ticker(product_code=self.product)['timestamp']
        time = time.replace("T", " ")

        w = pd.DataFrame([[balance, time, order_price]])

        w.to_csv(self.recording_path, index=False, encoding="utf-8",mode='a', header=False)    # append to the CSV

        print("資産：", str(balance), "売買価格：", str(order_price))


if __name__ == '__main__':

    rec = Recorder()

    while True:
        try:
            rec.market_recorder(rec.product, rec.path)  #
            time.sleep(0.5)
        except:
            time.sleep(2)
            import traceback
            traceback.print_exc()