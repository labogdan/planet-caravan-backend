from Lib.helpers import handleize


class ProductAttributeValue:

    def __init__(self, value):
        self.id = None
        self.value = value
        self.slug = handleize(value)