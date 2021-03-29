from Lib.helpers import handleize


class Category:
    def __init__(self, name):
        self.id = None
        self.name = name
        self.slug = handleize(name)
        self.description = ''
        self.lft = 0
        self.rght = 0
        self.tree_id = 0
        self.level = 0
        self.parent_id = None
        self.background_image = ''
        self.background_image_alt = ''
        self.description_json = '{}'
        self.children = []

    def __str__(self):

        children = "\n\t - " + "\n\t - ".join([str(c) for c in self.children]) if len(self.children) else ""
        return f'{self.id}: "{self.name}" ({self.slug}) || {self.lft}:{self.rght} {children}'