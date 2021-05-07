from Lib.helpers import handleize


class Product:

    def __init__(self, name=''):
        self.id = None
        self.name = name
        self.slug = handleize(name)
        self.description = ''
        self.description_json = ''
        self.product_type_id = None
        self.is_published = True
        self.category_id = None
        self.charge_taxes = True
        self.description_json = '{}'
        self.currency = 'USD'
        self.visible_in_listings = True
        self.metadata = '{}'
        self.private_metadata = '{}'
        self.description = ''

        self.variants = []
        self.attributes = []
        self.collections = []
        self.collection = None
        self.type = None
        self.category = None
