from Information import Information
from HistoricalData import HistoricalData
from Realtime_Data import RealtimeData
from datetime import datetime
from OrderMaker import OrderMaker
import traceback
import time
from decimal import *


class Commander(Information):

    """
    HitoricalDataとInformationから情報をもらってきて、実際に取引をこなうかどうか判断する。
    取引を行うと判断した場合には、OrderMakerへ指令を投げ、発注させる。
    HistoricalDataからはcsvに保存されている取引履歴を貰っている
    InformationからはAPIの情報をもらっている
    """

    def __init__(self):
        super().__init__()
        self.order_maker = OrderMaker()
        self.trade_history = HistoricalData()

        self.rd = RealtimeData()    # RealtimeDataのインスタンスを生成する
        self.df_tail = self.trade_history.df.tail(1)    # csvの最後の一行＝最新データを切り取る

        self.ewma_1day = self.df_tail['ewma1day']
        self.ewma_3days = self.df_tail['ewma3days']
        self.ewma_5days = self.df_tail['ewma5days']
        self.ewma_25days = self.df_tail['ewma25days']

        self.div_1day = self.df_tail['1dayDiv']
        self.div_5days = self.df_tail['5dayDiv']
        self.div_25days = self.df_tail['divergence']

        self.ewma_1hour = self.df_tail['ewma60mins']
        self.ewma_6hours = self.df_tail['ewma360mins']
        self.ewma_12hours = self.df_tail['ewma12hrs']

        self.order_side = None  # BUY or SELL

        self.current_price = self.rd.last_price

        self.orders = []            # 現在の注文が入る
        self.positions = []         # 現在のポジションが入る
        self.ordering_price = 0    # 注文中の価格が入る
        self.chart = {}             # 各種EWMAが入る

        self.market_flow = "SLEEP"     # 市場の流れ
        self.market_status = self.api.gethealth(product=self.product)['health']

        self.signal = False    # Trueならば取引GOサイン、Falseならば停止

        self.balance = self.api.getcollateral()['collateral']  # 証拠金残高、レバ１倍なのでそのまま余力

        self.order_id = None
        self.ordering = False   # 注文中か否か確認用
        self.positioning = False    # ポジションあるか否か確認用

        self.waiting_time = self.default_waiting_time      # キャンセルまでの待ち時間(sec)

    def market_reader(self):

        """
        現在、市場が上昇傾向なのか下落傾向なのかを判断する。
        """

        rd = self.rd  #
        rd.get_current_data()
        self.renew_chart_data()
        current_price = rd.last_price

        div = abs((current_price - self.chart['ewma_1day']) / self.chart['ewma_1day'] * 100)  # ewma1 に対する現在価格の乖離率

        if div <= 0:
            market = "SLEEP"
            print('DIVGERGENCE IS TOO LOW, WAIT FOR CLEAR MOVEMENT, DIVERGENCE PERCENTAGE:', div, '%')

        elif ((current_price > self.chart['ewma_1day'] > self.chart['ewma_3days']) or
              (self.chart['ewma_3days'] > self.chart['ewma_1day'] and current_price > self.chart['ewma_1day'])):
            market = "UP"
            self.order_side = "BUY"

        elif ((current_price < self.chart['ewma_1day'] < self.chart['ewma_3days']) or
              (self.chart['ewma_1days'] > self.chart['ewma_3days'] and self.chart['ewma_1day'] > current_price)):
            market = "DOWN"
            self.order_side = "SELL"

        else:
            market = "SLEEP"

        self.market_flow = market

    def renew_chart_data(self):

        """
        CSVに保存されているチャート情報が更新されていると思われるので、最新の状態を読み込みに行く
        かつ、これまで保持していた古い情報を最新の情報へアップデートする
        market_readerなどから使う
        """

        self.trade_history.renew_data()
        self.df_tail = self.trade_history.df.tail(1)

        self.ewma_1day = self.df_tail['ewma1day']
        self.ewma_3days = self.df_tail['ewma3days']
        self.ewma_5days = self.df_tail['ewma5days']
        self.ewma_25days = self.df_tail['ewma25days']

        self.div_1day = self.df_tail['1dayDiv']
        self.div_5days = self.df_tail['5dayDiv']
        self.div_25days = self.df_tail['divergence']

        self.ewma_1hour = self.df_tail['ewma60mins']
        self.ewma_6hours = self.df_tail['ewma360mins']
        self.ewma_12hours = self.df_tail['ewma12hrs']

        self.chart = {'ewma_1day': self.ewma_1day,
                      'ewma_3days': self.ewma_3days,
                      'ewma_5days': self.ewma_5days,
                      'ewma_25days': self.ewma_25days,
                      'div_1day': self.div_1day,
                      'div_5days': self.div_5days,
                      'div_25days': self.div_25days,
                      'ewma_1hour': self.ewma_1hour,
                      'ewma_6hours': self.ewma_6hours,
                      'ewma_12hours': self.ewma_12hours}

    def board_status_checker(self):

        """
        サーバーの負荷状態を確認し、負荷の強い状態のときは動きを止めさせる
        """

        self.market_status = self.api.gethealth(product=self.product)['health']

        if self.market_status == "NORMAL" or self.market_status == "BUSY":
            self.signal = True
        else:
            self.signal = False

    def sfd_status_checker(self):

        """
        現物とFXの価格乖離率を計算し、SFDが発動しそうならば取引をやめさせる
        """

        btc_price = self.api.board(product="BTC_JPY")['mid_price']
        self.rd.get_current_data()
        current_price = self.rd.last_price

        sfd = (current_price / btc_price) * 100     # 現物との価格乖離率

        if sfd > 4.7:
            self.signal = False
        else:
            self.signal = True

    def position_checker(self):

        """
        現在のポジションを確認し、すでにある場合には余計な発注動作をさせないようにする
        """

        positions = self.api.getpositions(product=self.product)

        if not positions:   # ポジションなし
            self.signal = True
            self.positioning = False
        else:                   # たまにゴミが残ることがあるので、そのときの処理を考えなければいけない -> only_position_checker
            self.signal = False
            self.positioning = True

        self.positions = positions

    def order_checker(self):
        """
        発注しているのかいないのか確認する
        :return:
        """

        self.orders = self.api.getparentorders(product=self.product,
                                               parent_order_state="ACTIVE")

        if not self.orders:
            self.signal = True
            self.ordering = False
        else:
            self.signal = False
            self.ordering = True
            self.order_id = self.orders[0]['parent_order_acceptance_id']     # 注文中ならばオーダーIDを取得しておく

    def only_position_checker(self):
        """
        ポジションだけがあり、注文がない状態になっていないか確認する
        →Trueならば決済注文を行う処理を呼び出す
        :return:
        """
        if self.positioning and self.ordering is False:

            position_size = 0

            for position in self.positions:
                position_size += position['size']     # 全ポジションを確実に解消

            position_price = self.positions[0]['price']    # 値段はまあよい
            position_side = self.positions[0]['side']

            if position_size < 0.001:
                position_size = 0.001 + position_size   # 0.001ビットコイン所持していれば次の注文で全部きれいになるはず

            position_size = Decimal(position_size).quantize(Decimal('0.0000'), rounding=ROUND_HALF_DOWN)

            position_size = float(position_size)

            order = self.order_maker.oco_order_maker(position_side, position_size, position_price)  # 決済注文を入れる

            time.sleep(2)

            print("OCO ORDER SENT FROM AUTOBOT:", order)

    def only_order_checker(self):
        """
        ポジションはないが、注文だけが行われている状態で発動する
        →発注から時間が経過していれば、一度注文を解除する指令を出す
        :return:
        """

        if self.ordering and self.positioning is False:
            ordered_time = self.orders[0]['parent_order_date']        # 注文を入れた時刻
            ordered_time = ordered_time.replace("T", " ")

            if ordered_time.find(".") == -1:
                ordered_time = datetime.strptime(ordered_time, '%Y-%m-%d %H:%M:%S')
                ordered_time = ordered_time.timestamp()
            else:
                ordered_time = datetime.strptime(ordered_time, '%Y-%m-%d %H:%M:%S.%f')
                ordered_time = ordered_time.timestamp()

            passed_time = datetime.now().timestamp() - ordered_time - 32400  # 注文を入れてからの経過時間

            print('Time till cancelling:', self.waiting_time - passed_time)

            executed = self.orders[0]['executed_size']       # 約定済みの分量がゼロでなければキャンセルはしない

            if passed_time > self.waiting_time and executed == 0:     # 一定時間以上約定なし
                self.order_maker.cancel_parent_order(self.order_id)
                self.waiting_time = self.default_waiting_time            # キャンセルできたらキャンセル待ち時間を初期設定に戻す

    def order_actually_dead_checker(self):
        """
        現在のBTC価格と、自分の発注価格とを比較する
        無理そうならばwaiting_timeを変更し、注文キャンセルの方向へ持っていく
        :return:
        """
        self.rd.get_current_data()
        self.current_price = self.rd.last_price

        self.ordering_price = self.orders[0]['price']   # 注文中の価格

        if abs(self.current_price - self.ordering_price) >= self.cancelling_line:
            self.waiting_time = 45
    
    def slippage_checker(self):
        """
        約定した注文と、現在のポジションの平均価格を比較してスリッページを確認する
        スリッページがあった場合には、一度注文をキャンセルして約定価格を変えさせる
        :return: 
        """
        ordered_price = self.orders[0]['price']
        average_price = self.orders[0]['average_price']

        if self.orders:
            if ordered_price != average_price and self.orders[0]['executed_size'] != 0:
                self.api.cancelparentorder(product_code=self.product,
                                           parent_order_id=self.order_id
                                           )
                print('-----------------------------ORDER CANCELLED DUE TO SLIPPAGE-------------------------------')
                time.sleep(1)


if __name__ == '__main__':
    commander = Commander()
    try:
        while True:
            commander.board_status_checker()      # とりあえず鯖状態を確認
            commander.sfd_status_checker()        # sfdを確認
            commander.renew_chart_data()          # 最新のewmaほかを手に入れる
            commander.order_checker()             # 注文中か否か
            commander.position_checker()          # ポジション確認
            commander.only_position_checker()     # ポジションしかない場合の動作を行う
            commander.order_actually_dead_checker()   # 注文が実質死亡していないか確認する
            commander.only_order_checker()        # 注文しかない場合の処理を行う →場合によってはここで注文をキャンセルする
            commander.slippage_checker()
    except:
        time.sleep(2)
        traceback.print_exc()
