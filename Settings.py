import api


class Settings:

    def __init__(self):
        self.api_key = api.api_key  # must be string
        self.api_secret = api.api_secret    # string too
        self.path = "bitflyer2.csv"    # ビットフウライヤーの取引履歴
        self.recording_path = "record.csv"     # 取引価格や口座残高を記録するところ
        self.product = "FX_BTC_JPY"
        self.realtime_product = "lightning_ticker_" + self.product
        self.lost_price = 3000  # 損切り価格
        self.cancelling_line = 2000     # 現在価格と注文価格の差がこれより大きくなったらwaiting_timeを変更する
        self.default_waiting_time = 600
        self.profit_price = 300
