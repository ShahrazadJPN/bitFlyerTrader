import pandas as pd
from datetime import datetime
from Settings import Settings


class HistoricalData(Settings):

    def __init__(self):  # Dataframeを作成する
        super().__init__()
        self.df = pd.read_csv(self.path,
                              header=None,
                              parse_dates=True,
                              date_parser=lambda x: datetime.fromtimestamp(float(x)),
                              index_col='datetime',
                              names=['datetime', 'price', 'amount'])

        self.df['ewma1day'] = self.df['price'].ewm(span=1440).mean()  # 1日の加重移動平均
        self.df['ewma5days'] = self.df['price'].ewm(span=7200).mean()  # だいたい5日あたりの加重移動平均
        self.df['ewma25days'] = self.df['price'].ewm(span=3600).mean()  # だいたい25日あたりの加重移動平均
        self.df['divergence'] = (self.df['price'] - self.df['ewma25days']) / self.df['ewma25days'] * 100  # 25日乖離率
        self.df['1dayDiv'] = (self.df['price'] - self.df['ewma1day']) / self.df['ewma1day'] * 100  # 1日乖離率
        self.df['5dayDiv'] = (self.df['price'] - self.df['ewma5days']) / self.df['ewma5days'] * 100  # 5日乖離率
        self.df['ewma3days'] = self.df['price'].ewm(span=4320).mean()  # 3日移動平均
        self.df['ewma12hrs'] = self.df['price'].ewm(span=720).mean()  # 6時間移動平均
        self.df['ewma60mins'] = self.df['price'].ewm(span=60).mean()  # 30分移動平均
        self.df['ewma360mins'] = self.df['price'].ewm(span=120).mean()  # 120分移動平均

        self.ewma_1day = self.df['ewma1day']
        self.ewma_3days = self.df['ewma3days']
        self.ewma_5days = self.df['ewma5days']
        self.ewma_25days = self.df['ewma25days']

        self.div_1day = self.df['1dayDiv']
        self.div_5days = self.df['5dayDiv']
        self.div_25days = self.df['divergence']

        self.ewma_1hour = self.df['ewma60mins']
        self.ewma_6hours = self.df['ewma360mins']
        self.ewma_12hours = self.df['ewma12hrs']

        self.length = len(self.df.index)

    def renew_data(self):

        self.df = pd.read_csv(self.path,  # CSVを読み込み直すことで最新の状態に更新する
                              header=None,
                              parse_dates=True,
                              date_parser=lambda x: datetime.fromtimestamp(float(x)),
                              index_col='datetime',
                              skiprows=(self.length - (self.length - 36000)),
                              names=['datetime', 'price', 'amount'])

        self.df['ewma1day'] = self.df['price'].ewm(span=1440).mean()  # 1日の加重移動平均
        self.df['ewma5days'] = self.df['price'].ewm(span=7200).mean()   # だいたい5日あたりの加重移動平均
        self.df['ewma25days'] = self.df['price'].ewm(span=3600).mean()  # だいたい25日あたりの加重移動平均
        self.df['divergence'] = (self.df['price'] - self.df['ewma25days']) / self.df['ewma25days'] * 100  # 25日乖離率
        self.df['1dayDiv'] = (self.df['price'] - self.df['ewma1day']) / self.df['ewma1day'] * 100  # 1日乖離率
        self.df['5dayDiv'] = (self.df['price'] - self.df['ewma5days']) / self.df['ewma5days'] * 100  # 5日乖離率
        self.df['ewma3days'] = self.df['price'].ewm(span=4320).mean()   # 3日移動平均
        self.df['ewma12hrs'] = self.df['price'].ewm(span=720).mean()   # 6時間移動平均
        self.df['ewma60mins'] = self.df['price'].ewm(span=60).mean()   # 30分移動平均
        self.df['ewma360mins'] = self.df['price'].ewm(span=120).mean()   # 120分移動平均

        self.ewma_1day = self.df['ewma1day']
        self.ewma_3days = self.df['ewma3days']
        self.ewma_5days = self.df['ewma5days']
        self.ewma_25days = self.df['ewma25days']

        self.div_1day = self.df['1dayDiv']
        self.div_5days = self.df['5dayDiv']
        self.div_25days = self.df['divergence']

        self.ewma_1hour = self.df['ewma60mins']
        self.ewma_6hours = self.df['ewma360mins']
        self.ewma_12hours = self.df['ewma12hrs']

        self.length = len(self.df.index)
