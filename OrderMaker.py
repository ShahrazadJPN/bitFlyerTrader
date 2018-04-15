from Information import Information
import time
from Recorder import Recorder


class OrderMaker(Information):
    """
    InformationからはAPIの情報だけをもらっておく
    実際にオーダーを行うときは、Mainから指令を受ける
    """
    def __init__(self):
        super().__init__()
        self.recorder = Recorder()

    def cancel_parent_order(self, order_id):
        """
        Nomen est omen
        :param order_id:
        :return:
        """
        self.api.cancelparentorder(product_code=self.product,
                                   parent_order_acceptance_id=order_id)
        time.sleep(2)

    def profit_price_decider(self, order_side, order_price):

        """
        発注する際の利確ラインを決定する
        :return:
        """

        board = self.api.board(product_code=self.product)

        asks = board['asks']
        bids = board['bids']

        ask_size = 0
        ask_price = 0

        bid_size = 0
        bid_price = 0

        default_target = 300

        bottom_line = 400  # 最低でもこの価格までは利確を待つ
        upper_line = 1200  # 最高でもこの価格までで利確する

        if order_side == "BUY":

            for ask in asks:
                if (bottom_line <= ask['price'] - order_price <= upper_line) and (ask['_size'] >= ask_size):
                    ask_size = ask['_size']
                    ask_price = ask['price']
                    if ask_size >= 2:
                        break

            if ask_price == 0:
                ask_price = order_price + default_target
            elif -100 <= int(order_price - ask_price) <= 100:
                ask_price += 200

            return int(ask_price - 10)

        elif order_side == "SELL":
            for bid in bids:
                if (bottom_line <= order_price - bid['price'] <= upper_line) and (bid['_size'] >= bid_size):
                    bid_size = bid['_size']
                    bid_price = bid['price']
                    if bid_size >= 2:
                        break

            if bid_price == 0:
                bid_price = order_price - default_target
            elif -100 <= int(order_price - bid_price) <= 100:
                bid_price -= 200

            return int(bid_price + 10)
        
    def oco_order_maker(self, order_side, order_size, order_price):

        data = self.order_base_maker(order_side, order_price)

        profit_or_loss = self.api.sendparentorder(
                                                  order_method="OCO",
                                                  parameters=[
                                                              {
                                                                  "product_code": self.product,
                                                                  "condition_type": "LIMIT",
                                                                  "side": data['execution_side'],  # 決済用
                                                                  "price": data['profit_line'],
                                                                  "size": order_size  # 所持しているビットコインの数量を入れる
                                                              },
                                                              {
                                                                  "product_code": self.product,
                                                                  "condition_type": "STOP",  # ストップ注文
                                                                  "side": data['execution_side'],
                                                                  "price": data['loss_line'],  # what?
                                                                  "trigger_price": data['loss_line'],
                                                                  "size": order_size
                                                              }
                                                             ]
        )

        if 'status' in profit_or_loss.keys():
            if profit_or_loss['status'] == -205:
                self.api.cancelallchildorders(product_code=self.product)
                print("ERROR OCCURRED, CANCELLING ALL ORDERS")
                time.sleep(2)

        return profit_or_loss
    
    def parent_order_maker(self, order_side, order_size, order_price, balance):

        data = self.order_base_maker(order_side, order_price)

        buy_btc = self.api.sendparentorder(
                                     order_method="IFDOCO",
                                     parameters=[{
                                         "product_code": self.product,
                                         "condition_type": "LIMIT",
                                         "side": order_side,
                                         "price": order_price,
                                         "size": order_size,
                                         'time_in_force': 'IOC'
                                     },
                                         {
                                             "product_code": self.product,
                                             "condition_type": "LIMIT",
                                             "side": data['execution_side'],  # 決済用
                                             "price": data['profit_line'],
                                             "size": order_size  # 所持しているビットコインの数量を入れる
                                         },
                                         {
                                             "product_code": self.product,
                                             "condition_type": "STOP",  # ストップ注文
                                             "side": data['execution_side'],
                                             "price": 0,  #
                                             "trigger_price": data['loss_line'],
                                             "size": order_size
                                         }]

                                     )

        print("ordered: " + order_side, str(order_size) + "BTC at the price of " + str(order_price))

        print(buy_btc)

        if 'status' in buy_btc.keys():
            if buy_btc['status'] == -205:
                self.api.cancelallchildorders(product_code=self.product)
                print("ERROR OCCURED, CANCELLING ALL ORDERS")
                time.sleep(2)

        self.recorder.balance_recorder(balance, order_price)
        print(buy_btc)
        time.sleep(1)

        return buy_btc

    def order_base_maker(self, order_side, order_price):

        loss = None
        contrary = None

        if order_side == "BUY":

            contrary = "SELL"

            loss = int(order_price - self.lost_price)  # 同上、損切ライン

        elif order_side == "SELL":

            contrary = "BUY"

            loss = int(order_price + self.lost_price)  # 同上、損切ライン

        profit = self.profit_price_decider(order_side, order_price)

        data = {'execution_side': contrary, 'loss_line': loss, 'profit_line': profit}

        return data

    def market_order_maker(self, order_size, order_side):

        market = self.api.sendchildorder(product_code=self.product,
                                         child_order_type='MARKET',
                                         side=order_side,
                                         size=order_size,
                                         time_in_force='IOC'
                                         )

        print(market)

        time.sleep(3.5)
