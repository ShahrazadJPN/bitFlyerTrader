from Information import Information
from HistoricalData import HistoricalData
# from Realtime_Data import RealtimeData
from datetime import datetime
from Recorder import Recorder
from OrderMaker import OrderMaker
import time
from decimal import *


class ConditionChecker(Information):

    """
    HitoricalDataとInformationから情報をもらってきて、取引すべき状態か否かチェックする。
    取引を行うと判断した場合には、OrderMakerへ指令を投げ、発注させる。
    HistoricalDataからはcsvに保存されている取引履歴を貰っている
    InformationからはAPIの情報をもらっている
    """

    def __init__(self):
        super().__init__()
        self.order_maker = OrderMaker()
        self.trade_history = HistoricalData()
        # self.rd = RealtimeData()    # RealtimeDataのインスタンスを生成する
        self.recorder = Recorder()

        self.df_tail = self.trade_history.df.tail(1)    # csvの最後の一行＝最新データを切り取る

        # self.ewma_1day = self.df_tail['ewma1day'][0]
        # self.ewma_3days = self.df_tail['ewma3days'][0]
        # self.ewma_5days = self.df_tail['ewma5days'][0]
        # self.ewma_25days = self.df_tail['ewma25days'][0]

        # self.div_1day = self.df_tail['1dayDiv'][0]
        # self.div_5days = self.df_tail['5dayDiv'][0]
        # self.div_25days = self.df_tail['divergence'][0]

        self.ewma_1hour = self.df_tail['ewma60mins'][0]
        self.ewma_6hours = self.df_tail['ewma360mins'][0]
        # self.ewma_12hours = self.df_tail['ewma12hrs'][0]

        self.ewma_1min = self.df_tail['ewma_1min'][0]
        self.ewma_5mins = self.df_tail['ewma_5mins'][0]

        self.best_bid = 0
        self.best_ask = 0

        self.order_side = 'BUY/SELL'  # Will be BUY or SELL

        self.current_price = self.api.board(product_code=self.product)['mid_price']

        self.orders = []            # 現在の注文が入る
        self.positions = []         # 現在のポジションが入る
        self.ordering_price = 0    # 注文中の価格が入る

        self.market_flow = "SLEEP"     # 市場の流れ
        self.market_status = self.api.gethealth(product_code=self.product)['status']

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

        # rd = self.rd  # RealtimeDataインスタンス
        # rd.get_current_data()
        self.renew_chart_data()
        self.current_price_getter()
        current_price = self.current_price

        # div = abs((current_price - self.chart['ewma_1day']) / self.chart['ewma_1day'] * 100)  # ewma1 に対する現在価格の乖離率

        # if div <= 0.5:
        #     market = "SLEEP"
        #     print('DIVGERGENCE IS TOO LOW, WAIT FOR CLEAR MOVEMENT, DIVERGENCE PERCENTAGE:', div, '%')

        if ((current_price > self.ewma_1min > self.ewma_5mins) or
            (self.ewma_5mins > self.ewma_1min and current_price > self.ewma_1min)):
            market = "UP"
            self.order_side = "BUY"

        elif ((current_price < self.ewma_1min < self.ewma_5mins) or
              (self.ewma_1min > self.ewma_5mins and self.ewma_1min > current_price)):
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

        # self.ewma_1day = self.df_tail['ewma1day'][0]
        # self.ewma_3days = self.df_tail['ewma3days'][0]
        # self.ewma_5days = self.df_tail['ewma5days'][0]
        # self.ewma_25days = self.df_tail['ewma25days'][0]
        #
        # self.div_1day = self.df_tail['1dayDiv'][0]
        # self.div_5days = self.df_tail['5dayDiv'][0]
        # self.div_25days = self.df_tail['divergence'][0]

        self.ewma_1hour = self.df_tail['ewma60mins'][0]
        self.ewma_6hours = self.df_tail['ewma360mins'][0]
        # self.ewma_12hours = self.df_tail['ewma12hrs'][0]

        self.ewma_1min = self.df_tail['ewma_1min'][0]
        self.ewma_5mins = self.df_tail['ewma_5mins'][0]

    def board_status_checker(self):

        """
        サーバーの負荷状態を確認し、負荷の強い状態のときは動きを止めさせる
        また、スプレッドが大きく開いている時にも止めさせる
        """

        self.market_status = self.api.gethealth(product_code=self.product)['status']

        if self.market_status == "NORMAL" or self.market_status == "BUSY":
            ticker = self.api.ticker(product_code=self.product)
            self.best_bid = ticker['best_bid']
            self.best_ask = ticker['best_ask']

            spread = (self.best_ask / self.best_bid - 1) * 100  # スプレッドの計算

            if spread < self.spread_limit:
                self.signal = True
            else:
                self.signal = False

        else:
            self.signal = False

    def sfd_status_checker(self):

        """
        現物とFXの価格乖離率を計算し、SFDが発動しそうならば取引をやめさせる
        """

        btc_price = self.api.board(product_code="BTC_JPY")['mid_price']
        self.current_price_getter()

        sfd = (self.current_price / btc_price - 1) * 100     # 現物との価格乖離率

        if sfd > 4.7:
            self.signal = False
        else:
            self.signal = True

    def position_checker(self):

        """
        現在のポジションを確認し、すでにある場合には余計な発注動作をさせないようにする
        """

        positions = self.api.getpositions(product_code=self.product)

        if not positions:   # ポジションなし
            self.signal = True
            self.positioning = False
        else:                   # ポジションあり
            self.signal = False
            self.positioning = True  # 購入サインを消し、ポジション有のフラグを立てる

        self.positions = positions

    def order_checker(self):
        """
        発注しているのかいないのか確認する
        :return:
        """

        self.orders = self.api.getparentorders(product_code=self.product,
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

            print("OCO ORDER SENT:", order)

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
        # self.rd.get_current_data()

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

    def current_price_getter(self):
        """
        ときどき現在価格を取得するための関数
        :return:
        """
        self.current_price = self.api.board(product_code=self.product)['mid_price']

    def order_information_checker(self, order_type):
        """
        注文に必要な情報を収集し、実際の注文指示を出す
        :param order_type:
        :return:
        """
        if self.market_flow == "UP":
            order_side = "BUY"
        elif self.market_flow == "DOWN":
            order_side = "SELL"
        else:
            order_side = "NONE"

        if order_side == "BUY" or order_side == "SELL":
            self.current_price_getter()
            purchasable_btc = self.balance / self.current_price
            order_size = Decimal(purchasable_btc).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
            order_size = float(order_size)
            order_price = self.current_price

            if order_type == "IFDOCO":

                self.order_maker.parent_order_maker(order_side, order_size, order_price, self.balance)

            elif order_type == "MARKET":

                self.order_maker.market_order_maker(order_size, order_side)

        else:
            pass

    def position_checker_for_market_ordering(self, current_price):
        """
        成行注文で取引する時のポジション状態を確認する
        ついでに注文も出す
        :return:
        """
        positions = self.positions

        position_size = 0

        for position in positions:
            position_size += position['size']     # 全ポジションを確実に解消

        position_side = positions[0]['side']

        if position_size < 0.001:
            position_size = 0.001 + position_size   # 0.001ビットコイン所持していれば次の注文で全部きれいになるはず

        position_size = Decimal(position_size).quantize(Decimal('0.0000'), rounding=ROUND_HALF_DOWN)

        position_size = float(position_size)

        order_size = position_size

        order_side = "BUY" if position_side == "SELL" else "SELL"

        position_price = positions[0]['price']

        go = self.market_order_go_or_not_checker(position_price, current_price, position_side)

        if go:
            self.order_maker.market_order_maker(order_size, order_side)

    def market_order_go_or_not_checker(self, position_price, current_price, position_side):

        if position_side == "BUY":  # 買いポジションを持っている時
            if current_price - position_price > self.profit_price:  # 利確
                return True
            elif abs(current_price - position_price) > self.lost_price:     # 損切り
                return True
            else:
                return False
        elif position_side == "SELL":  # 売りポジションを持っている時
            if position_price - current_price > self.profit_price:  # 利確
                return True
            elif abs(position_price - current_price) > self.lost_price:     # 損切り
                return True
            else:
                return False
        else:
            return False

    def child_order_checker(self):
        """
        発注しているのかいないのか確認する
        :return:
        """

        self.orders = self.api.getchildorders(product_code=self.product,
                                              child_order_state="ACTIVE")

        if not self.orders:
            self.signal = True
            self.ordering = False
        else:
            self.signal = False
            self.ordering = True
            self.order_id = self.orders[0]['child_order_acceptance_id']     # 注文中ならばオーダーIDを取得しておく
