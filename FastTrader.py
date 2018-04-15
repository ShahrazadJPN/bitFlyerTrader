from ConditionChecker import ConditionChecker
from pubnub.callbacks import SubscribeCallback
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub_tornado import PubNubTornado
from pubnub.pnconfiguration import PNReconnectionPolicy
from tornado import gen
from Settings import Settings
from OrderMaker import OrderMaker
from Recorder import Recorder

class FastTrader(Settings):

    last_price = 0
    hd = ConditionChecker()
    hd.market_reader()  # マーケットの流れを確認
    hd.board_status_checker()  # サーバー状態を確認
    hd.sfd_status_checker()  # SFDを確認
    rec = Recorder()
    count = 0
    count2 = 0
    last_balance = 0
    order = OrderMaker()

    def __init__(self):
        super().__init__()
        self.c = PNConfiguration()
        self.c.subscribe_key = 'sub-c-52a9ab50-291b-11e5-baaa-0619f8945a4f'
        self.c.reconnect_policy = PNReconnectionPolicy.LINEAR
        self.pubnub = PubNubTornado(self.c)
        channels = [
                    self.realtime_product,
                   ]
        self.main(channels)
        self.pubnub.start()

    @gen.coroutine
    def main(self, channels):

        class Callback(SubscribeCallback):

            def message(self, pubnub, message):
                current_price = message.message['ltp']
                FastTrader.hd.child_order_checker()
                FastTrader.hd.position_checker()
                if FastTrader.count == 0:
                    FastTrader.hd.market_reader()
                print(current_price)

                if FastTrader.hd.positioning and not FastTrader.hd.ordering:
                    FastTrader.hd.position_checker_for_market_ordering(current_price)
                    print('aiming to place execution order')
                FastTrader.count += 1

                if FastTrader.hd.signal:
                    print('aiming to place a new order')
                    FastTrader.hd.order_information_checker("MARKET")

                if FastTrader.count == 40:
                    FastTrader.count2 += 1
                    FastTrader.hd.sfd_status_checker()
                    if FastTrader.count2 == 10:
                        FastTrader.rec.balance_recorder(FastTrader.hd.balance, current_price)
                        FastTrader.count2 = 0
                    FastTrader.count = 0


        s = Callback()
        self.pubnub.add_listener(s)
        self.pubnub.subscribe().channels(channels).execute()

    def stop(self):
        self.pubnub.stop()

    def get_current_data(self):
        self.pubnub.start()


if __name__ == '__main__':
    while True:
        try:
            r = FastTrader()
        except:
            import time
            import traceback
            time.sleep(2)
            traceback.print_exc()