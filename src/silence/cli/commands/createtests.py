from silence.__main__ import CONFIG


def handle(args):
    from silence.server.test_creator import create_tests

    create_tests()
    print("Done!")
