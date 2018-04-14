from ConditionChecker import ConditionChecker
from pubnub.callbacks import SubscribeCallback
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub_tornado import PubNubTornado
from pubnub.pnconfiguration import PNReconnectionPolicy
from tornado import gen
from Settings import Settings


class FastTrader(Settings):

    last_price = 0
    hd = ConditionChecker()

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
                FastTrader.hd.market_reader()           # マーケットの流れを確認
                FastTrader.hd.board_status_checker()  # サーバー状態を確認
                FastTrader.hd.sfd_status_checker()  # SFDを確認
                print(FastTrader.hd.signal)
                print(current_price)
                if FastTrader.hd.signal:
                    print("yep")

        s = Callback()
        self.pubnub.add_listener(s)
        self.pubnub.subscribe().channels(channels).execute()

    def stop(self):
        self.pubnub.stop()

    def get_current_data(self):
        self.pubnub.start()


if __name__ == '__main__':
    r = FastTrader()