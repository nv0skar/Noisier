from silence.__main__ import CONFIG


def handle(args):
    from silence.server.endpoint_creator import create_api

    if CONFIG.get().general.auto_endpoints:
        print("Creating the default endpoints and generating the API filessilence.")
        create_api()
        print("Done!")
    else:
        print(
            "Endpoint auto generation is disabled in the settings, you need to enable it before you can use this command."
        )
