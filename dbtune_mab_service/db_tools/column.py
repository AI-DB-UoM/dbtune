class Column:
    def __init__(self, table_name, column_name, column_type):
        self.table_name = table_name
        self.column_name = column_name
        self.column_type = column_type
        self.column_size = None
        self.max_column_size = None
        self.is_pk = False

    def set_column_size(self, size):
        self.column_size = size

    def set_max_column_size(self,  max_size):
        self.max_column_size = max_size

    def set_is_primary_key(self, is_pk):
        self.is_pk = is_pk

    def get_id(self):
        return self.table_name + '_' + self.column_name

    @staticmethod
    def construct_id(table_name, column_name):
        return table_name + '_' + column_name

    def __repr__(self):
        return f"{self.column_name}: {self.column_type}, pk={self.is_pk}, size={self.column_size}"
