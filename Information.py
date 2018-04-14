import pybitflyer
from Settings import Settings


class Information(Settings):

    def __init__(self):
        super().__init__()
        self.api = pybitflyer.API(api_key=self.api_key, api_secret=self.api_secret)
