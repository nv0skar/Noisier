from silence.db.populate import create_database


def handle(args):
    print("Creating the database silence.")
    create_database()
    print("Done!")
