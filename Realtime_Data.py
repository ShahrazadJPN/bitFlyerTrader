from pubnub.callbacks import SubscribeCallback
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub_tornado import PubNubTornado
from pubnub.pnconfiguration import PNReconnectionPolicy
from tornado import gen
from Settings import Settings


class RealtimeData(Settings):

    last_price = 0

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
                RealtimeData.last_price = message.message['ltp']
                pubnub.stop()   # 必要なデータを取得したら一度停止する

        s = Callback()
        self.pubnub.add_listener(s)
        self.pubnub.subscribe().channels(channels).execute()

    def stop(self):
        self.pubnub.stop()

    def get_current_data(self):
        self.pubnub.start()


if __name__ == '__main__':
    r = RealtimeData()
