"""A small batch processor containing an intentional connection leak."""


def process_batch(batch_id, database):
    connection = database.connect()
    try:
        records = connection.fetch_records(batch_id)
    except TimeoutError:
        # Intentional bug: the timeout path re-raises before closing the connection.
        raise
    connection.close()
    return records
