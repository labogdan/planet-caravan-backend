from Lib.helpers import handleize


class ProductType():
    def __init__(self, ptype=''):
        super().__init__()
        self.type = ptype
        self.slug = handleize(ptype)
        self.variant_attributes = []
        self.attributes = []
        self.id = None

    def add_attribute(self, attribute):
        self.attributes.append(attribute)

    def add_variant_attribute(self, attribute):
        self.variant_attributes.append(attribute)

    def __str__(self):
        lst = "\n\t".join([str(a) for a in self.attributes])
        return f'{self.type}: {lst}'
