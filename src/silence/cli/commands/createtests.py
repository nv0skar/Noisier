from ...settings import settings


def handle(args):
    from ...server.test_creator import create_tests

    create_tests()
    print("Done!")
