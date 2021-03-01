from Lib.helpers import handleize

class ProductCollection:
    def __init__(self, name=''):
        super().__init__()
        self.name = name
        self.slug = handleize(name)
        self.id = None
