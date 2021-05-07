from Lib.helpers import handleize


class ProductAttribute:
    def __init__(self, type_name, values=None):
        self.type = type_name
        self.slug = handleize(type_name)
        self.values = values if values is not None else []
        self.id = None
        self.assignment_id = None


    def set_values(self, values):
        self.values = values

    def add_value(self, value):
        self.values.append(value)

    def __str__(self):
        return f'{self.type}: ({self.values})'
