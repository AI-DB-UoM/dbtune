class Table:
    def __init__(self, table_name, table_row_count, pk_columns):
        self.table_name = table_name
        self.table_row_count = table_row_count
        self.pk_columns = pk_columns
        self.columns = None

    def set_columns(self, columns):
        self.columns = columns

    def get_columns(self):
        if self.columns is None:
            raise Exception('Columns are not set')

        return self.columns

    def __str__(self):
        return (f"Table(name={self.table_name}, "
                f"rows={self.table_row_count}, "
                f"pk={self.pk_columns}, "
                f"columns={self.columns})")